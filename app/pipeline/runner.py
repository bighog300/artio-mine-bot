import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup
from redis import from_url
from rq import Worker
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.classifier import classify_page
from app.ai.client import OpenAIClient
from app.ai.confidence import score_record
from app.ai.extractors.artist import ArtistExtractor
from app.ai.extractors.artwork import ArtworkExtractor
from app.ai.extractors.event import EventExtractor
from app.ai.extractors.exhibition import ExhibitionExtractor
from app.ai.extractors.venue import VenueExtractor
from app.crawler.fetcher import fetch
from app.crawler.automated_crawler import AutomatedCrawler
from app.crawler.link_follower import crawl_source
from app.crawler.robots import RobotsChecker
from app.crawler.site_mapper import SiteMap, Section, map_site
from app.config import settings
from app.db import crud
from app.db.database import AsyncSessionLocal
from app.db.log_writer import configure_structlog_for_service
from app.db.models import Page, Record
from app.extraction.artist_merge import (
    ARTIST_RELATED_PAGE_TYPES,
    derive_artist_family_key,
    merge_artist_payload,
)
from app.extraction.artist_related import extract_artist_related_items
from app.metrics import metrics
from app.pipeline.image_collector import collect_images

worker_log_processor = configure_structlog_for_service("worker")
logger = structlog.get_logger()

# Map page_type to record_type for detail pages
DETAIL_PAGE_TYPES = {
    "artist_profile": "artist",
    "event_detail": "event",
    "exhibition_detail": "exhibition",
    "venue_profile": "venue",
    "artwork_detail": "artwork",
}
DISCOVERY_PAGE_TYPES = {
    "artist_directory_letter",
    "artist_profile_hub",
}
TERMINAL_PAGE_STATUSES = {"extracted", "skipped", "expanded"}


@dataclass
class ExtractionStats:
    records_created: int = 0
    records_failed: int = 0
    pages_processed: int = 0


class PipelineRunner:
    def __init__(
        self,
        db: AsyncSession,
        ai_client: OpenAIClient,
    ) -> None:
        self.db = db
        self.ai_client = ai_client
        self.robots_checker = RobotsChecker()
        self._extractors = {
            "artist": ArtistExtractor(ai_client),
            "event": EventExtractor(ai_client),
            "exhibition": ExhibitionExtractor(ai_client),
            "venue": VenueExtractor(ai_client),
            "artwork": ArtworkExtractor(ai_client),
        }
        self._crawl_hints_cache: dict[str, dict[str, Any]] = {}

    async def run_full_pipeline(self, source_id: str) -> None:
        """Run complete pipeline: map → crawl → extract."""
        if settings.environment == "production":
            raise RuntimeError("This task must run in a worker environment, not Vercel.")
        crawl_exception: Exception | None = None
        try:
            await crud.update_source(self.db, source_id, status="mapping")
            site_map = await self.run_map_site(source_id)

            await crud.update_source(self.db, source_id, status="crawling")
            try:
                await self.run_crawl(source_id, site_map=site_map)
            except Exception as exc:
                crawl_exception = exc
                logger.error("crawl_stage_error", source_id=source_id, error=str(exc))

            # Ensure crawl writes are committed before extraction reads pages.
            await self.db.commit()

            await crud.update_source(self.db, source_id, status="extracting")
            await self.run_extract(source_id)

            if crawl_exception is not None:
                raise RuntimeError(
                    f"crawl failed before extraction: {crawl_exception}"
                ) from crawl_exception

            await crud.update_source(
                self.db,
                source_id,
                status="done",
                last_crawled_at=datetime.now(UTC),
            )
            logger.info("pipeline_complete", source_id=source_id)
        except Exception as exc:
            logger.error("pipeline_error", source_id=source_id, error=str(exc))
            try:
                await crud.update_source(
                    self.db, source_id, status="error", error_message=str(exc)
                )
            except ValueError:
                logger.warning("pipeline_error_source_missing", source_id=source_id)
            raise

    async def run_map_site(self, source_id: str) -> SiteMap:
        """Map site structure and store in Source record."""
        if settings.environment == "production":
            raise RuntimeError("This task must run in a worker environment, not Vercel.")
        source = await crud.get_source(self.db, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")

        site_map = await map_site(source.url, ai_client=self.ai_client)

        # Store site_map as JSON
        site_map_data = {
            "root_url": site_map.root_url,
            "platform": site_map.platform,
            "sections": [
                {
                    "name": s.name,
                    "url": s.url,
                    "content_type": s.content_type,
                    "pagination_type": s.pagination_type,
                    "index_pattern": s.index_pattern,
                    "confidence": s.confidence,
                }
                for s in site_map.sections
            ],
        }
        await crud.update_source(self.db, source_id, site_map=json.dumps(site_map_data))
        logger.info("map_site_done", source_id=source_id, sections=len(site_map.sections))
        return site_map

    async def run_crawl(
        self,
        source_id: str,
        site_map: SiteMap | None = None,
    ) -> Any:
        """Crawl all pages for a source."""
        if settings.environment == "production":
            raise RuntimeError("This task must run in a worker environment, not Vercel.")
        source_exists = await crud.wait_for_source(
            self.db,
            source_id,
            retries=3,
            delay_seconds=0.2,
        )
        if source_exists is None:
            raise ValueError(f"Source {source_id} not found before crawl start")
        source = await crud.get_source(self.db, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")

        if source.structure_map:
            try:
                structure_map = json.loads(source.structure_map)
            except json.JSONDecodeError as exc:
                logger.warning("crawl_structure_map_invalid_json", source_id=source_id, error=str(exc))
                raise ValueError("Structure map JSON is invalid; re-run /analyze-structure endpoint") from exc

            try:
                crawler = AutomatedCrawler(structure_map, self.db, self.ai_client)
                stats = await crawler.execute_crawl_plan(source_id)
                pages_crawled = max(int(stats.get("pages_crawled", 0)), 1)
                deterministic_rate = stats.get("extracted_deterministic", 0) / pages_crawled
                ai_fallback_rate = stats.get("extracted_ai_fallback", 0) / pages_crawled
                failure_rate = stats.get("failed", 0) / pages_crawled
                logger.info(
                    "crawl_stats",
                    source_id=source_id,
                    pages_crawled=stats.get("pages_crawled", 0),
                    deterministic_rate=round(deterministic_rate, 4),
                    ai_fallback_rate=round(ai_fallback_rate, 4),
                    failure_rate=round(failure_rate, 4),
                    tokens_used=stats.get("tokens_used", 0),
                    cost=stats.get("cost", 0.0),
                )
                return stats
            except Exception as exc:
                logger.warning(
                    "automated_crawler_failed_falling_back",
                    source_id=source_id,
                    error=str(exc),
                )
        else:
            logger.info(
                "crawl_structure_map_missing_falling_back",
                source_id=source_id,
            )

        if site_map is None:
            if source and source.site_map:
                data = json.loads(source.site_map)
                site_map = SiteMap(
                    root_url=data["root_url"],
                    platform=data.get("platform", "unknown"),
                    sections=[Section(**s) for s in data.get("sections", [])],
                )
            else:
                source_obj = await crud.get_source(self.db, source_id)
                site_map = SiteMap(root_url=source_obj.url if source_obj else "")

        stats = await crawl_source(
            source_id=source_id,
            site_map=site_map,
            db=self.db,
            robots_checker=self.robots_checker,
        )
        pages_crawled = max(stats.pages_fetched, 1)
        fallback_stats = {"pages_crawled": stats.pages_fetched, "failed": stats.pages_error}
        logger.info(
            "crawl_stats",
            source_id=source_id,
            deterministic_rate=0.0,
            ai_fallback_rate=0.0,
            failure_rate=round(stats.pages_error / pages_crawled, 4),
            tokens_used=0,
            cost=0.0,
        )
        return fallback_stats

    async def run_extract(self, source_id: str) -> ExtractionStats:
        """Extract records from eligible pages that are not yet terminal."""
        if settings.environment == "production":
            raise RuntimeError("This task must run in a worker environment, not Vercel.")
        logger.info("extraction_started", source_id=source_id)
        status_result = await self.db.execute(
            select(Page.status, func.count(Page.id))
            .where(Page.source_id == source_id)
            .group_by(Page.status)
        )
        status_counts = {status: count for status, count in status_result.all()}
        pages = await crud.list_pages_by_statuses(
            self.db,
            source_id=source_id,
            statuses=["fetched", "classified"],
            limit=10000,
        )
        logger.info(
            "eligible_pages_count",
            source_id=source_id,
            count=len(pages),
            statuses=status_counts,
        )
        if len(pages) == 0:
            logger.warning(
                "no_pages_eligible_for_extraction",
                source_id=source_id,
            )
            logger.info(
                "page_status_distribution",
                source_id=source_id,
                statuses=status_counts,
            )
        stats = ExtractionStats()
        structure_map = await self._get_structure_map(source_id)

        for page in pages:
            try:
                record = await self.run_extraction_for_page(page, structure_map=structure_map)
                if record:
                    stats.records_created += 1
                stats.pages_processed += 1
            except Exception as exc:
                logger.error("extract_page_error", page_id=page.id, error=str(exc))
                stats.records_failed += 1

        logger.info(
            "pages_processed",
            source_id=source_id,
            pages_processed=stats.pages_processed,
            records_created=stats.records_created,
            records_failed=stats.records_failed,
        )
        metrics.increment("pages_processed", stats.pages_processed)
        metrics.increment("records_created", stats.records_created)
        total_records = await crud.count_records(self.db, source_id=source_id)
        await crud.update_source(self.db, source_id, total_records=total_records)
        return stats

    async def run_extraction_for_page(
        self,
        page: Page,
        *,
        structure_map: dict[str, Any] | None = None,
    ) -> Record | None:
        """Classify page, extract record, score confidence, store in DB."""
        if settings.environment == "production":
            raise RuntimeError("This task must run in a worker environment, not Vercel.")
        if not page.html:
            logger.warning(
                "page_extraction_skipped_no_html",
                source_id=page.source_id,
                page_id=page.id,
                url=page.url,
            )
            return None

        logger.info(
            "page_classified",
            source_id=page.source_id,
            page_id=page.id,
            url=page.url,
        )
        source_hints = await self._get_crawl_hints(page.source_id)
        if self._should_ignore_url(page.url, source_hints):
            await crud.update_page(self.db, page.id, status="skipped")
            return None

        forced_page_type = self._get_page_role_override(page.url, source_hints)
        expected_fields: list[str] | None = None
        if forced_page_type is not None:
            classify_result = type(
                "ForcedClassifyResult",
                (),
                {
                    "page_type": forced_page_type,
                    "confidence": 100,
                    "reasoning": "crawl_hints.page_role_overrides",
                },
            )()
        else:
            structured = self.classify_page_with_structure(page.url, structure_map)
            if structured is not None:
                classify_result = type(
                    "StructuredClassifyResult",
                    (),
                    {
                        "page_type": structured["page_type"],
                        "confidence": 100,
                        "reasoning": "structure_map.pattern_match",
                    },
                )()
                expected_fields = structured.get("expected_fields") or None
            else:
                classify_result = await classify_page(
                    url=page.url, html=page.html, ai_client=self.ai_client
                )
        logger.info(
            "page_classification_result",
            source_id=page.source_id,
            page_id=page.id,
            url=page.url,
            page_type=classify_result.page_type,
            confidence=classify_result.confidence,
        )
        await crud.update_page(
            self.db, page.id, page_type=classify_result.page_type, status="classified"
        )

        if classify_result.page_type in DISCOVERY_PAGE_TYPES:
            await self.handle_discovery_page(
                page,
                classify_result.page_type,
                source_hints=source_hints,
            )
            return None

        if self._is_force_deepen(page.url, source_hints):
            await self.deepen_same_slug_children(page, source_hints=source_hints)

        if classify_result.page_type in ARTIST_RELATED_PAGE_TYPES:
            return await self.process_artist_related_page(
                page,
                classify_result.page_type,
                final_status="extracted",
            )

        record_type = DETAIL_PAGE_TYPES.get(classify_result.page_type)
        if record_type is None:
            # Not a detail page — skip extraction
            await crud.update_page(self.db, page.id, status="skipped")
            logger.info(
                "page_skipped",
                source_id=page.source_id,
                page_id=page.id,
                url=page.url,
                page_type=classify_result.page_type,
            )
            return None

        # Extract
        extractor = self._extractors.get(record_type)
        if extractor is None:
            logger.warning(
                "page_extraction_skipped_missing_extractor",
                source_id=page.source_id,
                page_id=page.id,
                url=page.url,
                record_type=record_type,
            )
            return None

        existing_record = await crud.get_record_by_page_and_type(
            self.db,
            source_id=page.source_id,
            page_id=page.id,
            record_type=record_type,
        )
        if existing_record is not None:
            await crud.update_page(self.db, page.id, status="extracted", extracted_at=datetime.now(UTC))
            logger.info(
                "record_duplicate_skipped",
                source_id=page.source_id,
                page_id=page.id,
                record_id=existing_record.id,
                record_type=record_type,
            )
            metrics.increment("duplicate_items_skipped")
            return None

        try:
            context = {"expected_fields": expected_fields, "page_type": classify_result.page_type} if expected_fields else None
            data = await extractor.extract(url=page.url, html=page.html, context=context)
        except Exception as exc:
            logger.error("extractor_error", page_id=page.id, record_type=record_type, error=str(exc))
            existing_error_record = await crud.get_record_by_page_and_type(
                self.db,
                source_id=page.source_id,
                page_id=page.id,
                record_type=record_type,
            )
            if existing_error_record is None:
                await crud.create_record(
                    self.db,
                    source_id=page.source_id,
                    record_type=record_type,
                    page_id=page.id,
                    source_url=page.url,
                    status="error",
                    raw_error=str(exc),
                )
            await crud.update_page(self.db, page.id, status="error", error_message=str(exc))
            return None

        # Score confidence
        image_urls = data.pop("image_urls", [])
        score, band, reasons = score_record(record_type, data, image_urls)

        # Build record kwargs from extracted data
        record_kwargs: dict[str, Any] = {
            "page_id": page.id,
            "source_url": page.url,
            "status": "pending",
            "raw_data": json.dumps(data),
            "extraction_model": settings.openai_model,
            "extraction_provider": "openai",
            "confidence_score": score,
            "confidence_band": band,
            "confidence_reasons": json.dumps(reasons),
        }

        # Map extracted fields to record fields
        field_mapping = {
            "title": "title",
            "name": "title",
            "description": "description",
            "bio": "bio",
            "start_date": "start_date",
            "end_date": "end_date",
            "venue_name": "venue_name",
            "venue_address": "venue_address",
            "ticket_url": "ticket_url",
            "is_free": "is_free",
            "price_text": "price_text",
            "curator": "curator",
            "nationality": "nationality",
            "birth_year": "birth_year",
            "website_url": "website_url",
            "instagram_url": "instagram_url",
            "email": "email",
            "avatar_url": "avatar_url",
            "address": "address",
            "city": "city",
            "country": "country",
            "phone": "phone",
            "opening_hours": "opening_hours",
            "medium": "medium",
            "year": "year",
            "dimensions": "dimensions",
            "price": "price",
            "artist_name": "title",  # for artwork, use artist_name as subtitle reference
        }

        for src_field, dst_field in field_mapping.items():
            if src_field in data and data[src_field] is not None:
                record_kwargs[dst_field] = data[src_field]

        # Handle array fields
        for arr_field in ("artist_names", "mediums", "collections"):
            val = data.get(arr_field, [])
            if isinstance(val, list):
                record_kwargs[arr_field] = json.dumps(val)

        record = await crud.create_record(
            self.db,
            source_id=page.source_id,
            record_type=record_type,
            **record_kwargs,
        )
        logger.info(
            "record_created",
            source_id=page.source_id,
            page_id=page.id,
            record_id=record.id,
            record_type=record_type,
            confidence_score=score,
            confidence_band=band,
        )
        metrics.increment("records_created")

        await crud.update_page(
            self.db, page.id, status="extracted", extracted_at=datetime.now(UTC)
        )

        # Collect images
        try:
            await collect_images(
                record_id=record.id,
                page_url=page.url,
                html=page.html,
                image_urls=image_urls,
                db=self.db,
                source_id=page.source_id,
                page_id=page.id,
            )
        except Exception as exc:
            logger.warning("image_collection_error", record_id=record.id, error=str(exc))

        return record

    async def handle_discovery_page(
        self,
        page: Page,
        page_type: str,
        *,
        source_hints: dict[str, Any] | None = None,
    ) -> None:
        if page_type == "artist_directory_letter":
            await self.expand_artist_directory_letter(page, source_hints=source_hints)
        elif page_type == "artist_profile_hub":
            await self.deepen_same_slug_children(page, source_hints=source_hints)
        else:
            return
        await crud.update_page(self.db, page.id, status="expanded")
        metrics.increment("pages_expanded")
        logger.info(
            "directory_expanded",
            source_id=page.source_id,
            page_id=page.id,
            url=page.url,
            page_type=page_type,
        )

    async def expand_artist_directory_letter(
        self, page: Page, *, source_hints: dict[str, Any] | None = None
    ) -> None:
        if not page.html:
            return

        soup = BeautifulSoup(page.html, "lxml")
        base_netloc = urlparse(page.url).netloc
        for link in soup.find_all("a", href=True):
            href = (link.get("href") or "").strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            full_url = urljoin(page.url, href).split("#")[0]
            if self._should_ignore_url(full_url, source_hints or {}):
                continue
            parsed = urlparse(full_url)
            if parsed.netloc != base_netloc:
                continue
            segments = [segment for segment in parsed.path.split("/") if segment]
            if len(segments) != 1:
                continue
            slug = segments[0]
            if "." in slug:
                continue
            child_page, created = await crud.get_or_create_page(
                self.db,
                source_id=page.source_id,
                url=full_url,
            )
            if created or child_page.status not in TERMINAL_PAGE_STATUSES:
                await crud.update_page(
                    self.db,
                    child_page.id,
                    original_url=full_url,
                    status="pending",
                    depth=max(page.depth + 1, child_page.depth),
                )
                metrics.increment("pages_expanded")

    async def deepen_same_slug_children(
        self, page: Page, *, source_hints: dict[str, Any] | None = None
    ) -> None:
        base_url = page.url if page.url.endswith("/") else f"{page.url}/"
        suffixes = self._get_same_slug_children(page.url, source_hints or {})
        for suffix in suffixes:
            child_url = urljoin(base_url, suffix)
            if self._should_ignore_url(child_url, source_hints or {}):
                continue
            child_page, created = await crud.get_or_create_page(
                self.db,
                source_id=page.source_id,
                url=child_url,
            )
            if created or child_page.status not in TERMINAL_PAGE_STATUSES:
                await crud.update_page(
                    self.db,
                    child_page.id,
                    original_url=child_url,
                    status="pending",
                    depth=max(page.depth + 1, child_page.depth),
                )
                metrics.increment("pages_deepened")

            result = await fetch(child_url)
            if result.error:
                await crud.update_page(
                    self.db,
                    child_page.id,
                    status="error",
                    error_message=result.error,
                )
                logger.warning(
                    "discovery_child_fetch_error",
                    source_id=page.source_id,
                    parent_page_id=page.id,
                    page_id=child_page.id,
                    url=child_url,
                    error=result.error,
                )
                continue

            await crud.update_page(
                self.db,
                child_page.id,
                original_url=result.url,
                url=result.final_url,
                html=result.html,
                fetch_method=result.method,
                html_truncated=len(result.html.encode("utf-8")) >= 500 * 1024,
                status="fetched",
                depth=max(page.depth + 1, child_page.depth),
            )
            logger.info(
                "child_pages_fetched",
                source_id=page.source_id,
                parent_page_id=page.id,
                page_id=child_page.id,
                url=child_url,
            )
        logger.info(
            "hub_deepened",
            source_id=page.source_id,
            page_id=page.id,
            url=page.url,
            suffix_count=len(suffixes),
        )

    async def process_artist_related_page(
        self,
        page: Page,
        page_type: str,
        *,
        final_status: str = "extracted",
    ) -> Record | None:
        family_key = derive_artist_family_key(page.url)
        if family_key is None:
            raise ValueError(f"Unable to derive artist family key for URL {page.url}")

        extracted_data: dict[str, Any] = {}
        if page_type in {"artist_profile", "artist_profile_hub", "artist_biography"}:
            try:
                extracted_data = await self._extractors["artist"].extract(url=page.url, html=page.html or "")
            except Exception as exc:
                logger.error("extractor_error", page_id=page.id, record_type="artist", error=str(exc))
                existing_error_record = await crud.get_record_by_page_and_type(
                    self.db,
                    source_id=page.source_id,
                    page_id=page.id,
                    record_type="artist",
                )
                if existing_error_record is None:
                    await crud.create_record(
                        self.db,
                        source_id=page.source_id,
                        record_type="artist",
                        page_id=page.id,
                        source_url=page.url,
                        status="error",
                        raw_error=str(exc),
                    )
                await crud.update_page(self.db, page.id, status="error", error_message=str(exc))
                return None

        related_data = extract_artist_related_items(page_type, page.html or "", page.url)

        existing_page_artist = await crud.get_record_by_page_and_type(
            self.db,
            source_id=page.source_id,
            page_id=page.id,
            record_type="artist",
        )
        existing_artist = existing_page_artist
        if existing_artist is None:
            existing_artist = await crud.get_artist_record_by_family_key(
                self.db,
                source_id=page.source_id,
                family_key=family_key,
            )
        existing_raw = existing_artist.raw_data if existing_artist else None
        merged_payload = merge_artist_payload(
            existing_raw_data=existing_raw,
            page_type=page_type,
            source_url=page.url,
            source_page_id=page.id,
            extracted_data=extracted_data,
            related_data=related_data,
        )
        merged_payload["artist_family_key"] = family_key
        logger.info(
            "enrichment_merged",
            source_id=page.source_id,
            page_id=page.id,
            family_key=family_key,
            page_type=page_type,
        )
        metrics.increment("records_enriched")
        metrics.observe_completeness(merged_payload.get("completeness_score", 0))
        if merged_payload.get("conflicts"):
            logger.info(
                "conflicts_detected",
                source_id=page.source_id,
                page_id=page.id,
                family_key=family_key,
                conflict_fields=sorted(list(merged_payload.get("conflicts", {}).keys())),
            )

        artist_kwargs: dict[str, Any] = {
            "page_id": existing_artist.page_id if existing_artist else page.id,
            "source_url": page.url,
            "status": "pending",
            "raw_data": json.dumps(merged_payload),
            "title": merged_payload.get("artist_payload", {}).get("artist_name"),
            "bio": merged_payload.get("artist_payload", {}).get("bio_full")
            or merged_payload.get("artist_payload", {}).get("bio_short"),
            "website_url": merged_payload.get("artist_payload", {}).get("website"),
            "email": merged_payload.get("artist_payload", {}).get("email"),
            "nationality": merged_payload.get("artist_payload", {}).get("nationality"),
            "avatar_url": merged_payload.get("artist_payload", {}).get("avatar_url"),
            "confidence_score": merged_payload.get("completeness_score", 0),
            "confidence_band": "HIGH"
            if merged_payload.get("completeness_score", 0) >= 70
            else "MEDIUM"
            if merged_payload.get("completeness_score", 0) >= 40
            else "LOW",
            "confidence_reasons": json.dumps(
                [f"Completeness score {merged_payload.get('completeness_score', 0)}"]
            ),
        }

        if existing_artist is None:
            artist_record = await crud.create_record(
                self.db,
                source_id=page.source_id,
                record_type="artist",
                **artist_kwargs,
            )
        else:
            artist_record = await crud.update_record(self.db, existing_artist.id, **artist_kwargs)

        await self._create_artist_related_child_records(
            source_id=page.source_id,
            page=page,
            related_data=related_data,
        )
        logger.info(
            "completeness_calculated",
            source_id=page.source_id,
            page_id=page.id,
            completeness_score=merged_payload.get("completeness_score", 0),
            missing_fields=merged_payload.get("missing_fields", []),
        )

        await crud.update_page(
            self.db,
            page.id,
            status=final_status,
            extracted_at=datetime.now(UTC),
        )
        return artist_record

    async def _create_artist_related_child_records(
        self,
        *,
        source_id: str,
        page: Page,
        related_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        record_type_map = {
            "exhibitions": "exhibition",
            "articles": "artist_article",
            "press": "artist_press",
            "memories": "artist_memory",
        }
        for key, record_type in record_type_map.items():
            for item in related_data.get(key, []):
                fingerprint = item.get("item_fingerprint")
                if not fingerprint:
                    continue
                existing = await crud.get_record_by_item_fingerprint(
                    self.db,
                    source_id=source_id,
                    page_id=page.id,
                    record_type=record_type,
                    item_fingerprint=fingerprint,
                )
                if existing is not None:
                    metrics.increment("duplicate_items_skipped")
                    continue
                await crud.create_record(
                    self.db,
                    source_id=source_id,
                    page_id=page.id,
                    record_type=record_type,
                    title=item.get("title"),
                    description=item.get("raw_text"),
                    source_url=item.get("url") or item.get("source_url") or page.url,
                    raw_data=json.dumps(item),
                    status="pending",
                    confidence_score=60,
                    confidence_band="MEDIUM",
                    confidence_reasons=json.dumps(["Deterministic related-item extraction"]),
                )
                metrics.increment("records_created")
                logger.info(
                    "child_pages_created",
                    source_id=source_id,
                    page_id=page.id,
                    record_type=record_type,
                    fingerprint=fingerprint,
                )

    async def rerun_artist_family(self, source_id: str, family_key: str) -> dict[str, Any]:
        pages = await crud.list_pages_for_artist_family(
            self.db,
            source_id=source_id,
            family_key=family_key,
        )
        rerun_count = 0
        for page in pages:
            if page.page_type in ARTIST_RELATED_PAGE_TYPES:
                await crud.update_page(
                    self.db,
                    page.id,
                    status="classified",
                    error_message=None,
                )
                final_status = "expanded" if page.page_type == "artist_profile_hub" else "extracted"
                await self.process_artist_related_page(
                    page=page,
                    page_type=page.page_type,
                    final_status=final_status,
                )
                rerun_count += 1
        return {"family_key": family_key, "pages_reprocessed": rerun_count}

    async def _get_structure_map(self, source_id: str) -> dict[str, Any] | None:
        source = await crud.get_source(self.db, source_id)
        if source is None or not source.structure_map:
            return None
        try:
            return json.loads(source.structure_map)
        except json.JSONDecodeError:
            logger.warning("source_structure_invalid_json", source_id=source_id)
            return None

    def classify_page_with_structure(
        self,
        url: str,
        structure_map: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not structure_map:
            return None
        mining_map = structure_map.get("mining_map", {})
        for page_type, config in mining_map.items():
            pattern = config.get("url_pattern")
            if not pattern:
                continue
            if self._matches_pattern_url(url, pattern):
                return {"page_type": page_type, "expected_fields": config.get("expected_fields", [])}
        return None

    def _matches_pattern_url(self, url: str, pattern: str) -> bool:
        parsed_url = urlparse(url)
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
        return re.search(f"{escaped}$", parsed_url.path, flags=re.IGNORECASE) is not None

    async def _get_crawl_hints(self, source_id: str) -> dict[str, Any]:
        cached = self._crawl_hints_cache.get(source_id)
        if cached is not None:
            return cached
        source = await crud.get_source(self.db, source_id)
        hints: dict[str, Any] = {}
        if source and source.crawl_hints:
            try:
                loaded = json.loads(source.crawl_hints)
                if isinstance(loaded, dict):
                    hints = loaded
            except json.JSONDecodeError:
                hints = {}
        self._crawl_hints_cache[source_id] = hints
        return hints

    def _get_page_role_override(self, url: str, hints: dict[str, Any]) -> str | None:
        overrides = hints.get("page_role_overrides") or {}
        if not isinstance(overrides, dict):
            return None
        return overrides.get(url)

    def _is_force_deepen(self, url: str, hints: dict[str, Any]) -> bool:
        force_urls = hints.get("force_deepen_urls") or []
        if not isinstance(force_urls, list):
            return False
        return url in force_urls

    def _get_same_slug_children(self, url: str, hints: dict[str, Any]) -> list[str]:
        default_suffixes = [
            "about.php",
            "exhibitions.php",
            "articles.php",
            "press.php",
            "memories.php",
        ]
        custom_suffixes = hints.get("same_slug_children")
        if isinstance(custom_suffixes, list) and custom_suffixes:
            return [s for s in custom_suffixes if isinstance(s, str) and s.strip()]

        parsed = urlparse(url)
        domain_rules = hints.get("domain_rules") or {}
        if isinstance(domain_rules, dict):
            domain_hint = domain_rules.get(parsed.netloc) or {}
            domain_children = domain_hint.get("same_slug_children")
            if isinstance(domain_children, list) and domain_children:
                return [s for s in domain_children if isinstance(s, str) and s.strip()]
        return default_suffixes

    def _should_ignore_url(self, url: str, hints: dict[str, Any]) -> bool:
        patterns = hints.get("ignore_url_patterns") or []
        if not isinstance(patterns, list):
            return False
        return any(isinstance(pattern, str) and pattern in url for pattern in patterns)


async def _run_pipeline_job_async(
    job_id: str,
    source_id: str,
    job_type: str,
    payload: dict[str, Any],
) -> None:
    del payload  # reserved for future task-specific options
    await worker_log_processor.start()

    try:
        async with AsyncSessionLocal() as db:
            source = await crud.wait_for_source(db, source_id, retries=3, delay_seconds=0.2)
            if source is None:
                logger.error(
                    "pipeline_job_missing_source",
                    job_id=job_id,
                    source_id=source_id,
                    job_type=job_type,
                )
                return
            job = await crud.wait_for_job(db, job_id, retries=3, delay_seconds=0.2)
            if job is None:
                logger.error(
                    "pipeline_job_missing_job_row",
                    job_id=job_id,
                    source_id=source_id,
                    job_type=job_type,
                )
                return

            ai_client = OpenAIClient()
            runner = PipelineRunner(db=db, ai_client=ai_client)
            try:
                await crud.update_job_status(
                    db,
                    job_id,
                    "running",
                    started_at=datetime.now(UTC),
                )
            except ValueError:
                logger.error("pipeline_job_missing_job_row_on_start", job_id=job_id, source_id=source_id)
                return

            try:
                if job_type == "run_full_pipeline":
                    await runner.run_full_pipeline(source_id)
                    result = {"status": "done"}
                elif job_type == "map_site":
                    site_map = await runner.run_map_site(source_id)
                    result = {"sections": len(site_map.sections)}
                elif job_type == "crawl_section":
                    result = await runner.run_crawl(source_id)
                elif job_type == "extract_page":
                    stats = await runner.run_extract(source_id)
                    result = {
                        "records_created": stats.records_created,
                        "records_failed": stats.records_failed,
                        "pages_processed": stats.pages_processed,
                    }
                else:
                    raise ValueError(f"Unsupported job type: {job_type}")

                await crud.update_job_status(
                    db,
                    job_id,
                    "done",
                    result=result,
                    completed_at=datetime.now(UTC),
                )
            except Exception as exc:
                logger.exception("pipeline_job_failed", job_id=job_id, error=str(exc))
                try:
                    await crud.update_job_status(
                        db,
                        job_id,
                        "failed",
                        error_message=str(exc),
                        completed_at=datetime.now(UTC),
                    )
                except ValueError:
                    logger.warning(
                        "pipeline_job_failed_status_update_skipped",
                        job_id=job_id,
                        source_id=source_id,
                    )
                raise
    finally:
        await worker_log_processor.stop()


def process_pipeline_job(
    job_id: str,
    source_id: str,
    job_type: str,
    payload: dict[str, Any],
) -> None:
    import asyncio

    asyncio.run(_run_pipeline_job_async(job_id, source_id, job_type, payload))


def main() -> None:
    redis_url = os.environ.get("REDIS_URL", settings.redis_url)
    redis_conn = from_url(redis_url)
    worker = Worker(["default"], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    main()
