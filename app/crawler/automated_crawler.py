"""Deterministic crawler that executes AI-generated structure maps."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crawler.fetcher import fetch
from app.crawler.site_structure_analyzer import _generate_urls_from_pattern
from app.db import crud

logger = structlog.get_logger()


class AutomatedCrawler:
    """Execute AI-generated crawl plans using deterministic extraction."""

    def __init__(self, structure_map: dict[str, Any], db: AsyncSession, ai_client=None):
        self.structure_map = structure_map
        self.db = db
        self.ai_client = ai_client
        self.extraction_rules = structure_map.get("extraction_rules", {}) or {}
        self.stats = {
            "pages_crawled": 0,
            "extracted_deterministic": 0,
            "extracted_ai_fallback": 0,
            "failed": 0,
            "tokens_used": 0,
            "cost": 0.0,
        }
        self._ai_fallback_used = 0

    async def execute_crawl_plan(self, source_id: str) -> dict[str, Any]:
        """Execute crawl_targets and store extracted metadata on crawled pages."""
        source = await crud.get_source(self.db, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")

        crawl_targets = self.structure_map.get("crawl_targets", [])
        if not isinstance(crawl_targets, list):
            logger.warning("crawl_targets_invalid", source_id=source_id)
            return self.stats

        seen: set[str] = set()
        for target in crawl_targets:
            urls = self._urls_from_target(source.url, target)
            for url in urls:
                if url in seen:
                    continue
                seen.add(url)
                if len(seen) > settings.max_pages_per_source:
                    logger.info("max_pages_reached", source_id=source_id, limit=settings.max_pages_per_source)
                    return self.stats
                await self._process_url(source_id=source_id, url=url)

        return self.stats

    async def _process_url(self, source_id: str, url: str) -> None:
        result = await fetch(url)
        self.stats["pages_crawled"] += 1

        page_type = self._classify_by_url(url)
        html = result.html or ""
        title = self._extract_title(html)
        truncated_html = html.replace("\x00", "")[: 500 * 1024]

        try:
            page, created = await crud.get_or_create_page(self.db, source_id=source_id, url=url)
            if created:
                await crud.update_page(
                    self.db,
                    page.id,
                    status="fetched",
                    page_type=page_type,
                    title=title,
                    html=truncated_html,
                    fetch_method=result.method,
                    crawled_at=datetime.now(UTC),
                    error_message=result.error,
                )
            else:
                await crud.update_page(
                    self.db,
                    page.id,
                    page_type=page_type,
                    title=title,
                    html=truncated_html,
                    fetch_method=result.method,
                    crawled_at=datetime.now(UTC),
                    error_message=result.error,
                )

            deterministic = self._extract_deterministic(html, page_type, url)
            if deterministic["confidence"] >= settings.deterministic_confidence_threshold:
                self.stats["extracted_deterministic"] += 1
            elif self._should_use_ai_fallback():
                ai_result = await self._extract_with_ai(
                    html,
                    page_type,
                    context=f"url={url}",
                )
                if ai_result.get("data"):
                    self.stats["extracted_ai_fallback"] += 1
                self._ai_fallback_used += 1
            else:
                self.stats["failed"] += 1
        except Exception as exc:
            logger.error("automated_crawl_page_failed", source_id=source_id, url=url, error=str(exc))
            self.stats["failed"] += 1

    def _extract_deterministic(self, html: str, page_type: str, url: str) -> dict[str, Any]:
        """Extract using CSS selectors and regex (NO AI)."""
        soup = BeautifulSoup(html or "", "lxml")
        rules = self.extraction_rules.get(page_type, {}) or {}

        extracted: dict[str, Any] = {"data": {}, "confidence": 100, "method": "deterministic"}
        parse_failures = 0

        for field, selector in (rules.get("css_selectors", {}) or {}).items():
            try:
                elements = soup.select(selector)
                if not elements:
                    extracted["confidence"] -= 10
                    continue
                if len(elements) == 1:
                    extracted["data"][field] = elements[0].get_text(" ", strip=True)
                else:
                    extracted["data"][field] = [element.get_text(" ", strip=True) for element in elements]
            except Exception as exc:
                parse_failures += 1
                extracted["confidence"] -= 10
                logger.warning(
                    "deterministic_css_parse_failed",
                    url=url,
                    page_type=page_type,
                    field=field,
                    selector=selector,
                    error=str(exc),
                )

        text = soup.get_text("\n", strip=True)
        for field, pattern in (rules.get("regex_patterns", {}) or {}).items():
            try:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    extracted["data"][field] = match.group(1) if match.groups() else match.group(0)
                else:
                    extracted["confidence"] -= 10
            except re.error as exc:
                parse_failures += 1
                extracted["confidence"] -= 10
                logger.warning(
                    "deterministic_regex_parse_failed",
                    url=url,
                    page_type=page_type,
                    field=field,
                    pattern=pattern,
                    error=str(exc),
                )

        extracted["confidence"] = max(extracted["confidence"] - (parse_failures * 5), 0)
        return extracted

    async def _extract_with_ai(self, html: str, page_type: str, context: str) -> dict[str, Any]:
        """Fallback extraction path (called only when deterministic confidence is low)."""
        if self.ai_client is None:
            return {"data": {}, "confidence": 0, "method": "none"}
        user_content = (
            f"Context: {context}\n"
            f"Page type hint: {page_type}\n"
            "Extract key fields into JSON with shape {\"data\": {...}, \"confidence\": <0-100>}.\n"
            f"HTML snippet:\n{html[:5000]}"
        )
        try:
            response = await self.ai_client.complete(
                system_prompt="Extract structured data for an art website page using the provided page type hint.",
                user_content=user_content,
                response_format={"type": "json_object"},
            )
            return {
                "data": response.get("data", response),
                "confidence": int(response.get("confidence", 60)),
                "method": "ai_fallback",
            }
        except Exception as exc:
            logger.error("ai_fallback_failed", page_type=page_type, error=str(exc))
            return {"data": {}, "confidence": 0, "method": "ai_failed"}

    def _classify_by_url(self, url: str) -> str:
        """Classify page type by URL patterns from mining_map (NO AI)."""
        mining_map = self.structure_map.get("mining_map", {}) or {}
        parsed_url = urlparse(url)
        for page_type, config in mining_map.items():
            pattern = (config or {}).get("url_pattern")
            if not pattern:
                continue
            escaped = re.escape(pattern)
            token_map = {
                re.escape("[letter]"): r"[a-z]",
                re.escape("[number]"): r"\d+",
                re.escape("[page]"): r"\d+",
                re.escape("[name]"): r"[^/]+",
                re.escape("[id]"): r"[^/]+",
            }
            for token, regex in token_map.items():
                escaped = escaped.replace(token, regex)
            if re.search(f"{escaped}$", parsed_url.path, flags=re.IGNORECASE):
                return page_type
        return "unknown"

    def _urls_from_target(self, base_url: str, target: Any) -> list[str]:
        if isinstance(target, str):
            pattern = target
            limit = settings.max_pages_per_source
        elif isinstance(target, dict):
            pattern = target.get("url_pattern") or target.get("pattern") or target.get("url")
            limit = int(target.get("limit", settings.max_pages_per_source))
        else:
            return []
        if not pattern:
            return []
        return _generate_urls_from_pattern(base_url, pattern, limit=limit)

    def _should_use_ai_fallback(self) -> bool:
        return (
            settings.crawler_use_ai_fallback
            and self._ai_fallback_used < settings.max_ai_fallback_per_source
        )

    def _extract_title(self, html: str) -> str | None:
        if not html:
            return None
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        if title_tag is None:
            return None
        return title_tag.get_text(strip=True) or None
