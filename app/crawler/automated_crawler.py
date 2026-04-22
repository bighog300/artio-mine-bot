"""Deterministic crawler that executes AI-generated structure maps."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crawler import durable_frontier
from app.crawler.site_structure_analyzer import _generate_urls_from_pattern
from app.db import crud
from app.pipeline.image_collector import collect_images

logger = structlog.get_logger()

async def fetch(url: str):
    """Compatibility wrapper so tests can patch automated_crawler.fetch."""
    return await durable_frontier.fetch(url)


REVIEW_REASON_UNMAPPED = "unmapped_page_type"
REVIEW_REASON_LOW_CONFIDENCE = "low_confidence_extraction"
REVIEW_REASON_SELECTOR_MISS = "selector_miss"


class AutomatedCrawler:
    """Execute AI-generated crawl plans using deterministic extraction."""

    def __init__(
        self,
        structure_map: dict[str, Any],
        db: AsyncSession,
        ai_client=None,
        *,
        ai_allowed: bool = True,
        mapping_version_id: str | None = None,
    ):
        self.structure_map = structure_map
        self.crawl_plan = structure_map.get("crawl_plan", {}) or {}
        self.extraction_rules = structure_map.get("extraction_rules", {}) or {}
        self.follow_rules = structure_map.get("follow_rules", {}) or {}
        self.asset_rules = structure_map.get("asset_rules", {}) or {}
        self.db = db
        self.ai_client = ai_client
        self.ai_allowed = ai_allowed
        self.mapping_version_id = mapping_version_id
        self.stats: dict[str, Any] = {
            "pages_crawled": 0,
            "extracted_deterministic": 0,
            "extracted_ai_fallback": 0,
            "failed": 0,
            "skipped_unchanged": 0,
            "queued_for_review": 0,
            "tokens_used": 0,
            "cost": 0.0,
            "media_assets_captured": 0,
            "phase_stats": {},
        }
        self._ai_fallback_used = 0
        self._seen_urls: set[str] = set()
        self._phase_urls: dict[str, set[str]] = {}

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
                    await self._crawl_and_extract(source_id, url, depth=0)

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
        follow_from_phase = phase.get("follow_from_phase")
        before = int(self.stats.get("pages_crawled", 0))
        attempted = 0

        if pagination == "alpha":
            letters = "abcdefghijklmnopqrstuvwxyz"
            discovered: set[str] = set()
            for letter in letters:
                letter_url = urljoin(base_url, pattern.replace("[letter]", letter))
                attempted += 1
                await self._crawl_and_extract(source_id, letter_url, depth=0)
                self._phase_urls.setdefault(phase_name, set()).add(letter_url)
                discovered.update(await self._discover_links_from_url(letter_url, pattern))
            for url in sorted(discovered):
                attempted += 1
                await self._crawl_and_extract(source_id, url, depth=0)
                self._phase_urls.setdefault(phase_name, set()).add(url)
        elif pagination == "follow_links":
            discovered = await self._discover_links_for_follow_phase(
                source_id=source_id,
                pattern=pattern,
                follow_from_phase=follow_from_phase if isinstance(follow_from_phase, str) else None,
                fallback_url=base_url,
            )
            for url in sorted(discovered):
                attempted += 1
                await self._crawl_and_extract(source_id, url, depth=0)
                self._phase_urls.setdefault(phase_name, set()).add(url)
        else:
            urls = self._generate_urls(base_url, pattern, pagination, num_pages)
            for url in urls:
                attempted += 1
                await self._crawl_and_extract(source_id, url, depth=0)
                self._phase_urls.setdefault(phase_name, set()).add(url)

        pages_crawled = int(self.stats.get("pages_crawled", 0)) - before
        phase_stats = self.stats.setdefault("phase_stats", {})
        phase_stats[phase_name] = {
            "pages_crawled": max(0, pages_crawled),
            "urls_attempted": attempted,
        }
        logger.info("phase_complete", phase=phase_name, pages_crawled=max(0, pages_crawled), urls_attempted=attempted)

    async def _discover_links_for_follow_phase(
        self,
        *,
        source_id: str,
        pattern: str,
        follow_from_phase: str | None,
        fallback_url: str,
    ) -> set[str]:
        discovered: set[str] = set()
        source_urls = self._phase_urls.get(follow_from_phase or "", set())
        if source_urls:
            pages = await crud.list_pages(self.db, source_id=source_id, limit=settings.max_pages_per_source)
            for page in pages:
                if page.url not in source_urls or not page.html:
                    continue
                discovered.update(self._extract_internal_links_from_html(page.html, page.url, pattern))
        if discovered:
            return discovered
        if not fallback_url:
            return set()
        return await self._discover_links_from_url(fallback_url, pattern)

    async def _discover_links_from_url(self, url: str, pattern: str) -> set[str]:
        result = await fetch(url)
        if not result.html:
            return set()
        return self._extract_internal_links_from_html(result.html, url, pattern)

    def _extract_internal_links_from_html(self, html: str, current_url: str, pattern: str) -> set[str]:
        soup = BeautifulSoup(html or "", "lxml")
        current_netloc = urlparse(current_url).netloc
        discovered: set[str] = set()
        for node in soup.select("a[href]"):
            href = (node.get("href") or "").strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            full_url = urljoin(current_url, href).split("#")[0]
            parsed = urlparse(full_url)
            if parsed.netloc != current_netloc:
                continue
            if pattern and not self._matches_pattern(parsed.path, pattern):
                continue
            discovered.add(full_url)
        return discovered

    async def _crawl_and_extract(self, source_id: str, url: str, *, depth: int = 0) -> None:
        """Crawl URL and extract data deterministically."""
        if url in self._seen_urls:
            return
        self._seen_urls.add(url)
        if len(self._seen_urls) > settings.max_pages_per_source:
            return
        try:
            result = await fetch(url)
            if not result.html:
                self.stats["failed"] += 1
                logger.warning("fetch_failed", url=url, error=result.error)
                return

            html = result.html
            content_hash = hashlib.sha256((html or "").encode("utf-8")).hexdigest()
            self.stats["pages_crawled"] += 1

            page_type = self._classify_by_url(url)
            deterministic = self._extract_deterministic(html, page_type, url)
            asset_urls = self._extract_asset_urls(html=html, page_type=page_type, base_url=url)
            if asset_urls:
                deterministic.setdefault("data", {})
                deterministic["data"]["image_urls"] = list(asset_urls)
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
                if (
                    page.content_hash == content_hash
                    and page.mapping_version_id_used == self.mapping_version_id
                ):
                    self.stats["skipped_unchanged"] += 1
                    await crud.update_page(
                        self.db,
                        page.id,
                        status="skipped",
                        review_reason=None,
                        review_status=None,
                    )
                    return
                await crud.update_page(self.db, page.id, **updates)
            await crud.update_page(
                self.db,
                page.id,
                content_hash=content_hash,
                classification_method="deterministic_url_rules",
                extraction_method="deterministic_selectors_regex",
                mapping_version_id_used=self.mapping_version_id,
            )

            if page_type == "unknown":
                self.stats["failed"] += 1
                self.stats["queued_for_review"] += 1
                await crud.update_page(
                    self.db,
                    page.id,
                    status="needs_review",
                    review_reason=REVIEW_REASON_UNMAPPED,
                    review_status="queued",
                )
                return

            if confidence >= settings.deterministic_confidence_threshold:
                self.stats["extracted_deterministic"] += 1
                record = await self._save_record(source_id, page.id, page_type, deterministic, url)
                if record is not None and asset_urls:
                    try:
                        collected = await collect_images(
                            record_id=record.id,
                            page_url=url,
                            html=html,
                            image_urls=list(asset_urls),
                            db=self.db,
                            source_id=source_id,
                            page_id=page.id,
                        )
                        self.stats["media_assets_captured"] += len(collected)
                    except Exception as exc:
                        logger.debug("automated_crawler_collect_images_failed", page_id=page.id, error=str(exc))
                await self._follow_links(source_id=source_id, page_type=page_type, html=html, current_url=url, depth=depth)
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
                await self._follow_links(source_id=source_id, page_type=page_type, html=html, current_url=url, depth=depth)
                return

            logger.warning("skipping_low_confidence", url=url, confidence=confidence)
            self.stats["failed"] += 1
            self.stats["queued_for_review"] += 1
            await crud.update_page(
                self.db,
                page.id,
                status="needs_review",
                review_reason=REVIEW_REASON_LOW_CONFIDENCE if confidence > 0 else REVIEW_REASON_SELECTOR_MISS,
                review_status="queued",
            )
        except Exception as exc:
            logger.error("crawl_extract_failed", url=url, error=str(exc))
            self.stats["failed"] += 1

    async def _follow_links(
        self,
        *,
        source_id: str,
        page_type: str,
        html: str,
        current_url: str,
        depth: int,
    ) -> None:
        rules = self.follow_rules.get(page_type, {}) or {}
        selectors = list(rules.get("selectors", []) or [])
        selectors.extend(list(rules.get("pagination_selectors", []) or []))
        if not selectors:
            return
        max_depth = int(rules.get("max_depth", 1))
        if depth >= max_depth:
            return
        soup = BeautifulSoup(html or "", "lxml")
        discovered: set[str] = set()
        current_netloc = urlparse(current_url).netloc
        for selector in selectors:
            try:
                nodes = soup.select(selector)
            except Exception:
                continue
            for node in nodes:
                href = (node.get("href") or "").strip()
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                full_url = urljoin(current_url, href).split("#")[0]
                if urlparse(full_url).netloc != current_netloc:
                    continue
                if full_url in self._seen_urls:
                    continue
                discovered.add(full_url)
        for next_url in discovered:
            await self._crawl_and_extract(source_id, next_url, depth=depth + 1)

    def _extract_asset_urls(self, *, html: str, page_type: str, base_url: str) -> set[str]:
        rules = self.asset_rules.get(page_type, {}) or {}
        selectors = list(rules.get("selectors", []) or [])
        if not selectors:
            return set()
        soup = BeautifulSoup(html or "", "lxml")
        urls: set[str] = set()
        for selector in selectors:
            try:
                nodes = soup.select(selector)
            except Exception:
                continue
            for node in nodes:
                attr_candidates = ["src", "data-src", "href"]
                for attr in attr_candidates:
                    value = (node.get(attr) or "").strip()
                    if not value or value.startswith("data:"):
                        continue
                    full_url = urljoin(base_url, value).split("#")[0]
                    urls.add(full_url)
                    break
        return urls

    def _classify_by_url(self, url: str) -> str:
        """Classify page type by URL pattern matching (NO AI)."""
        parsed_path = urlparse(url).path

        best_page_type: str | None = None
        best_score = -1

        # Prefer extraction rule identifiers if available.
        for page_type, rules in self.extraction_rules.items():
            identifiers = rules.get("identifiers", [])
            for pattern in identifiers:
                if not self._matches_pattern(parsed_path, pattern):
                    continue
                score = self._pattern_specificity(pattern)
                if score > best_score:
                    best_score = score
                    best_page_type = page_type
        if best_page_type is not None:
            return best_page_type

        # Backward compatible mining_map pattern matching.
        mining_map = self.structure_map.get("mining_map", {}) or {}
        for page_type, config in mining_map.items():
            pattern = (config or {}).get("url_pattern")
            if not pattern or not self._matches_pattern(parsed_path, pattern):
                continue
            score = self._pattern_specificity(pattern)
            if score > best_score:
                best_score = score
                best_page_type = page_type

        return best_page_type or "unknown"

    def _pattern_specificity(self, pattern: str) -> int:
        normalized = pattern or ""
        normalized = normalized.replace("[letter]", "x")
        normalized = normalized.replace("[number]", "1")
        normalized = normalized.replace("[page]", "1")
        normalized = normalized.replace("[name]", "x")
        normalized = normalized.replace("[id]", "x")
        return len(normalized)

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
        extractor_cls = mapping.get(page_type, EventExtractor if "event" in page_type else ArtistExtractor)
        return extractor_cls(self.ai_client)

    def _get_ai_context(self, page_type: str) -> str:
        """Generate AI context hint for extraction."""
        rules = self.extraction_rules.get(page_type, {}) or {}
        hint = rules.get("ai_context_hint", "")
        expected_type = rules.get("expected_output_type", page_type)
        fields = ", ".join((rules.get("css_selectors", {}) or {}).keys())

        return f"Page type: {expected_type}\n{hint}\nExpected fields: {fields}"

    def _resolve_record_type(self, page_type: str) -> str:
        type_rules = self.structure_map.get("page_type_rules", {}) or {}
        page_rule = type_rules.get(page_type, {}) or {}
        explicit = page_rule.get("target_record_type")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip().lower()
        targets = page_rule.get("target_record_types") or page_rule.get("destination_entities") or []
        if isinstance(targets, list):
            for target in targets:
                if isinstance(target, str) and target.strip():
                    return target.strip().lower()

        mining_map = self.structure_map.get("mining_map", {}) or {}
        config = mining_map.get(page_type, {}) or {}
        for key in ("target_record_type", "record_type", "entity"):
            value = config.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()

        legacy = {
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
        }
        if page_type in legacy:
            return legacy[page_type]
        return "organization"

    async def _save_record(
        self,
        source_id: str,
        page_id: str | None,
        page_type: str,
        data: dict[str, Any],
        url: str,
    ) -> Any:
        """Save extracted record to database."""
        payload = data.get("data", {}) if isinstance(data.get("data"), dict) else {}
        title = payload.get("name") or payload.get("title")
        description = payload.get("bio") or payload.get("description")
        record_type = self._resolve_record_type(page_type)

        if page_id is not None:
            existing = await crud.get_record_by_page_and_type(
                self.db,
                source_id=source_id,
                page_id=page_id,
                record_type=record_type,
            )
            if existing is not None:
                return existing

        return await crud.create_record(
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
        regex = pattern.strip()
        if regex.lower().startswith("url matches "):
            regex = regex[len("URL matches "):].strip()
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
            self.ai_allowed
            and
            self.ai_client is not None
            and settings.crawler_allow_ai
            and settings.crawler_use_ai_fallback
            and self._ai_fallback_used < settings.max_ai_fallback_per_source
        )
