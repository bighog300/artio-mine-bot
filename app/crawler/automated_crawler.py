"""Deterministic crawler that executes AI-generated structure maps."""

from __future__ import annotations

import json
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
        self.crawl_plan = structure_map.get("crawl_plan", {}) or {}
        self.extraction_rules = structure_map.get("extraction_rules", {}) or {}
        self.db = db
        self.ai_client = ai_client
        self.stats: dict[str, Any] = {
            "pages_crawled": 0,
            "extracted_deterministic": 0,
            "extracted_ai_fallback": 0,
            "failed": 0,
            "tokens_used": 0,
            "cost": 0.0,
        }
        self._ai_fallback_used = 0

    async def execute_crawl_plan(self, source_id: str) -> dict[str, Any]:
        """Execute the AI-generated crawl plan."""
        logger.info("starting_crawl_plan", source_id=source_id)

        phases = self.crawl_plan.get("phases", [])
        if phases:
            for phase in phases:
                await self._execute_phase(source_id, phase)
        else:
            # Backward compatibility with Phase 1 structure maps.
            source = await crud.get_source(self.db, source_id)
            if source is None:
                raise ValueError(f"Source {source_id} not found")
            seen: set[str] = set()
            for target in self.structure_map.get("crawl_targets", []):
                for url in self._urls_from_target(source.url, target):
                    if url in seen:
                        continue
                    seen.add(url)
                    if len(seen) > settings.max_pages_per_source:
                        logger.info(
                            "max_pages_reached",
                            source_id=source_id,
                            limit=settings.max_pages_per_source,
                        )
                        break
                    await self._crawl_and_extract(source_id, url)

        logger.info(
            "crawl_complete",
            source_id=source_id,
            pages_crawled=self.stats["pages_crawled"],
            extracted_deterministic=self.stats["extracted_deterministic"],
            extracted_ai_fallback=self.stats["extracted_ai_fallback"],
            failed=self.stats["failed"],
        )
        return self.stats

    async def _execute_phase(self, source_id: str, phase: dict[str, Any]) -> None:
        """Execute a single crawl phase."""
        phase_name = phase.get("phase_name", "unnamed")
        logger.info("executing_phase", phase=phase_name)

        base_url = phase.get("base_url", "")
        pattern = phase.get("url_pattern", "")
        pagination = phase.get("pagination_type", "none")
        num_pages = int(phase.get("num_pages", 1))

        urls = self._generate_urls(base_url, pattern, pagination, num_pages)
        for url in urls:
            await self._crawl_and_extract(source_id, url)

    async def _crawl_and_extract(self, source_id: str, url: str) -> None:
        """Crawl URL and extract data deterministically."""
        try:
            result = await fetch(url)
            if not result.html:
                self.stats["failed"] += 1
                logger.warning("fetch_failed", url=url, error=result.error)
                return

            html = result.html
            self.stats["pages_crawled"] += 1

            page_type = self._classify_by_url(url)
            deterministic = self._extract_deterministic(html, page_type, url)
            confidence = int(deterministic.get("confidence", 0))

            page, created = await crud.get_or_create_page(self.db, source_id=source_id, url=url)
            updates = {
                "status": "fetched",
                "page_type": page_type,
                "title": self._extract_title(html),
                "html": html.replace("\x00", "")[: 500 * 1024],
                "fetch_method": result.method,
                "crawled_at": datetime.now(UTC),
                "error_message": result.error,
            }
            if created:
                await crud.update_page(self.db, page.id, **updates)
            else:
                await crud.update_page(self.db, page.id, **updates)

            if confidence >= settings.deterministic_confidence_threshold:
                self.stats["extracted_deterministic"] += 1
                await self._save_record(source_id, page.id, page_type, deterministic, url)
                return

            if self._should_use_ai_fallback():
                ai_data = await self._extract_with_ai(
                    html=html,
                    page_type=page_type,
                    context=self._get_ai_context(page_type),
                )
                self.stats["extracted_ai_fallback"] += 1
                self._ai_fallback_used += 1
                await self._save_record(source_id, page.id, page_type, ai_data, url)
                return

            logger.warning("skipping_low_confidence", url=url, confidence=confidence)
            self.stats["failed"] += 1
        except Exception as exc:
            logger.error("crawl_extract_failed", url=url, error=str(exc))
            self.stats["failed"] += 1

    def _classify_by_url(self, url: str) -> str:
        """Classify page type by URL pattern matching (NO AI)."""
        parsed_path = urlparse(url).path

        # Prefer extraction rule identifiers if available.
        for page_type, rules in self.extraction_rules.items():
            identifiers = rules.get("identifiers", [])
            if any(self._matches_pattern(parsed_path, pattern) for pattern in identifiers):
                return page_type

        # Backward compatible mining_map pattern matching.
        mining_map = self.structure_map.get("mining_map", {}) or {}
        for page_type, config in mining_map.items():
            pattern = (config or {}).get("url_pattern")
            if pattern and self._matches_pattern(parsed_path, pattern):
                return page_type

        return "unknown"

    def _extract_deterministic(self, html: str, page_type: str, url: str) -> dict[str, Any]:
        """Extract data using CSS selectors and regex (NO AI)."""
        soup = BeautifulSoup(html or "", "lxml")
        rules = self.extraction_rules.get(page_type, {}) or {}

        extracted: dict[str, Any] = {
            "page_type": page_type,
            "url": url,
            "confidence": 100,
            "data": {},
            "method": "deterministic",
        }

        css_selectors = rules.get("css_selectors", {}) or {}
        for field, selector in css_selectors.items():
            try:
                elements = soup.select(selector)
                if not elements:
                    extracted["confidence"] -= 10
                    continue
                if len(elements) == 1:
                    extracted["data"][field] = elements[0].get_text(" ", strip=True)
                else:
                    extracted["data"][field] = [el.get_text(" ", strip=True) for el in elements]
            except Exception as exc:
                logger.warning("css_selector_failed", selector=selector, error=str(exc), url=url)
                extracted["confidence"] -= 10

        text = soup.get_text("\n", strip=True)
        regex_patterns = rules.get("regex_patterns", {}) or {}
        for field, pattern in regex_patterns.items():
            try:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    extracted["data"][field] = match.group(1) if match.groups() else match.group(0)
                else:
                    extracted["confidence"] -= 10
            except re.error as exc:
                logger.warning("regex_failed", pattern=pattern, error=str(exc), url=url)
                extracted["confidence"] -= 10

        extracted["confidence"] = max(0, int(extracted["confidence"]))
        return extracted

    async def _extract_with_ai(self, html: str, page_type: str, context: str) -> dict[str, Any]:
        """Fallback: Extract using AI (only when CSS/regex fails)."""
        if self.ai_client is None:
            return {
                "page_type": page_type,
                "data": {},
                "confidence": 0,
                "method": "none",
            }

        extractor = self._get_extractor_for_page_type(page_type)
        try:
            extracted = await extractor.extract(
                url="https://placeholder.local/",
                html=html,
                context={"hint": context},
            )
            return {
                "page_type": page_type,
                "data": extracted,
                "confidence": int(extracted.get("confidence_score", 70)),
                "method": "ai_fallback",
            }
        except Exception as exc:
            logger.error("ai_fallback_failed", page_type=page_type, error=str(exc))
            return {
                "page_type": page_type,
                "data": {},
                "confidence": 0,
                "method": "ai_failed",
            }

    def _get_extractor_for_page_type(self, page_type: str):
        from app.ai.extractors.artist import ArtistExtractor
        from app.ai.extractors.artwork import ArtworkExtractor
        from app.ai.extractors.event import EventExtractor
        from app.ai.extractors.exhibition import ExhibitionExtractor
        from app.ai.extractors.venue import VenueExtractor

        mapping = {
            "artist_profile": ArtistExtractor,
            "artist": ArtistExtractor,
            "event_detail": EventExtractor,
            "event": EventExtractor,
            "exhibition_detail": ExhibitionExtractor,
            "exhibition": ExhibitionExtractor,
            "venue_profile": VenueExtractor,
            "venue": VenueExtractor,
            "artwork_detail": ArtworkExtractor,
            "artwork": ArtworkExtractor,
        }
        extractor_cls = mapping.get(page_type, ArtistExtractor)
        return extractor_cls(self.ai_client)

    def _get_ai_context(self, page_type: str) -> str:
        """Generate AI context hint for extraction."""
        rules = self.extraction_rules.get(page_type, {}) or {}
        hint = rules.get("ai_context_hint", "")
        expected_type = rules.get("expected_output_type", page_type)
        fields = ", ".join((rules.get("css_selectors", {}) or {}).keys())

        return f"Page type: {expected_type}\n{hint}\nExpected fields: {fields}"

    async def _save_record(
        self,
        source_id: str,
        page_id: str | None,
        page_type: str,
        data: dict[str, Any],
        url: str,
    ) -> None:
        """Save extracted record to database."""
        payload = data.get("data", {}) if isinstance(data.get("data"), dict) else {}
        title = payload.get("name") or payload.get("title")
        description = payload.get("bio") or payload.get("description")
        record_type = {
            "artist_profile": "artist",
            "artist": "artist",
            "event_detail": "event",
            "event": "event",
            "exhibition_detail": "exhibition",
            "exhibition": "exhibition",
            "venue_profile": "venue",
            "venue": "venue",
            "artwork_detail": "artwork",
            "artwork": "artwork",
        }.get(page_type, "artist")

        if page_id is not None:
            existing = await crud.get_record_by_page_and_type(
                self.db,
                source_id=source_id,
                page_id=page_id,
                record_type=record_type,
            )
            if existing is not None:
                return

        await crud.create_record(
            self.db,
            source_id=source_id,
            page_id=page_id,
            record_type=record_type,
            title=title,
            description=description,
            raw_data=json.dumps(payload),
            confidence_score=int(data.get("confidence", 50)),
            source_url=url,
            extraction_provider=data.get("method", "deterministic"),
        )

    def _generate_urls(self, base_url: str, pattern: str, pagination: str, num_pages: int) -> list[str]:
        """Generate concrete URLs from pattern."""
        if pagination == "letter":
            return [urljoin(base_url, pattern.replace("[letter]", ltr)) for ltr in "abcdefghijklmnopqrstuvwxyz"]
        if pagination == "numbered":
            return [urljoin(base_url, pattern.replace("[page]", str(page))) for page in range(1, num_pages + 1)]
        if pagination == "calendar":
            return [
                urljoin(base_url, pattern.replace("[month]", str(month).zfill(2)))
                for month in range(1, 13)
            ]
        return [urljoin(base_url, pattern)]

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Match URL/path against identifier pattern."""
        regex = pattern
        replacements = {
            "[letter]": "[a-z]",
            "[name]": "[a-z0-9-]+",
            "[page]": r"\\d+",
            "[number]": r"\\d+",
            "[year]": r"\\d{4}",
            "[month]": r"\\d{1,2}",
            "[id]": r"[^/]+",
        }
        for token, expression in replacements.items():
            regex = regex.replace(token, expression)
        try:
            return bool(re.search(regex, value, re.IGNORECASE))
        except re.error as exc:
            logger.warning("url_pattern_invalid", pattern=pattern, error=str(exc))
            return False

    def _extract_title(self, html: str) -> str | None:
        if not html:
            return None
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        if title_tag is None:
            return None
        return title_tag.get_text(strip=True) or None

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
            self.ai_client is not None
            and settings.crawler_allow_ai
            and settings.crawler_use_ai_fallback
            and self._ai_fallback_used < settings.max_ai_fallback_per_source
        )
