import json
import os
import re
import socket
from asyncio import sleep
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
from app.pipeline.job_progress import report_job_progress
from app.queue import QueueUnavailableError, get_default_queue

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
MAX_CONCURRENT_JOBS = int(os.environ.get("MAX_CONCURRENT_JOBS", str(settings.max_concurrent_jobs)))
WORKER_ID = os.environ.get("WORKER_ID", f"{socket.gethostname()}-{os.getpid()}")


@dataclass
class ExtractionStats:
    records_created: int = 0
    records_updated: int = 0
    records_failed: int = 0
    pages_processed: int = 0
    deterministic_hits: int = 0
    deterministic_misses: int = 0
    media_assets_captured: int = 0
    entity_links_created: int = 0


class PipelineRunner:
    def __init__(
        self,
        db: AsyncSession,
        ai_client: OpenAIClient | None,
        *,
        job_id: str | None = None,
        source_id: str | None = None,
    ) -> None:
        self.db = db
        self.ai_client = ai_client
        self.job_id = job_id
        self.source_id = source_id
        self.robots_checker = RobotsChecker()
        self._extractors = (
            {
                "artist": ArtistExtractor(ai_client),
                "event": EventExtractor(ai_client),
                "exhibition": ExhibitionExtractor(ai_client),
                "venue": VenueExtractor(ai_client),
                "artwork": ArtworkExtractor(ai_client),
            }
            if ai_client is not None
            else {}
        )
        self._crawl_hints_cache: dict[str, dict[str, Any]] = {}

    async def _control_checkpoint(self) -> None:
        if not self.job_id:
            return
        while True:
            job = await crud.get_job(self.db, self.job_id)
            if job is None:
                raise RuntimeError(f"Job {self.job_id} not found")
            if job.status == "cancelled":
                raise RuntimeError("Job cancelled by operator")
            if job.status != "paused":
                return
            await self._report(
                stage=job.current_stage or "paused",
                item=job.current_item,
                message="Job paused by operator",
                event_type="job_heartbeat",
            )
            await sleep(1)

    async def _report(
        self,
        *,
        stage: str | None = None,
        item: str | None = None,
        message: str | None = None,
        progress_current: int | None = None,
        progress_total: int | None = None,
        metrics_payload: dict[str, Any] | None = None,
        event_type: str = "progress",
        level: str = "info",
    ) -> None:
        if not self.job_id:
            return
        await report_job_progress(
            self.db,
            self.job_id,
            source_id=self.source_id,
            worker_id=WORKER_ID,
            stage=stage,
            item=item,
            message=message,
            progress_current=progress_current,
            progress_total=progress_total,
            metrics=metrics_payload,
            event_type=event_type,
            level=level,
        )

    async def run_full_pipeline(self, source_id: str) -> None:
        """Run complete pipeline: map → crawl → extract."""
        if settings.environment == "production":
            raise RuntimeError("This task must run in a worker environment, not Vercel.")
        crawl_exception: Exception | None = None
        try:
            await self._control_checkpoint()
            runtime_map, runtime_map_source = await crud.get_active_runtime_map(self.db, source_id)
            has_runtime_map = crud.has_usable_runtime_map_payload(runtime_map)
            mode = "deterministic" if has_runtime_map or self.ai_client is None else "ai_assisted"
            await self._report(
                stage="starting",
                item=source_id,
                message=f"Runtime mode selected: {mode}",
                event_type="runtime_mode_selected",
                metrics_payload={
                    "mode": mode,
                    "runtime_map_source": runtime_map_source,
                    "has_runtime_map": has_runtime_map,
                },
            )
            site_map: SiteMap | None = None
            if has_runtime_map:
                await self._report(
                    stage="mapping",
                    item=source_id,
                    message="Skipping AI mapping; existing runtime map loaded",
                    event_type="ai_mapping_skipped_existing_runtime_map",
                    metrics_payload={
                        "mode": "deterministic",
                        "runtime_map_source": runtime_map_source,
                    },
                )
            else:
                if self.ai_client is None or not settings.crawler_allow_ai:
                    await self._report(
                        stage="mapping",
                        item=source_id,
                        message="Runtime map missing and AI unavailable",
                        event_type="runtime_map_missing",
                        level="error",
                    )
                    raise RuntimeError(
                        "No usable runtime map exists for source and AI mapping is unavailable."
                    )
                await self._report(
                    stage="mapping",
                    item=source_id,
                    message="Starting site mapping",
                    event_type="stage_changed",
                )
                await crud.update_source(self.db, source_id, status="mapping")
                site_map = await self.run_map_site(source_id)

            await self._control_checkpoint()
            await self._report(
                stage="crawling",
                item=source_id,
                message="Starting crawl stage",
                event_type="stage_changed",
            )
            await crud.update_source(self.db, source_id, status="crawling")
            try:
                await self.run_crawl(source_id, site_map=site_map)
            except Exception as exc:
                crawl_exception = exc
                logger.error("crawl_stage_error", source_id=source_id, error=str(exc))

            # Ensure crawl writes are committed before extraction reads pages.
            await self.db.commit()

            await self._control_checkpoint()
            await self._report(
                stage="extracting",
                item=source_id,
                message="Starting extraction stage",
                event_type="stage_changed",
            )
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
            await self._report(
                stage="finalizing",
                item=source_id,
                message="Pipeline completed",
                event_type="job_completed",
                progress_current=100,
                progress_total=100,
            )
            logger.info("pipeline_complete", source_id=source_id)
        except Exception as exc:
            logger.error("pipeline_error", source_id=source_id, error=str(exc))
            await self._report(
                stage="finalizing",
                item=source_id,
                message=f"Pipeline failed: {exc}",
                event_type="job_failed",
                level="error",
            )
            try:
                await crud.update_source(
                    self.db, source_id, status="error", error_message=str(exc)
                )
            except ValueError:
                logger.warning("pipeline_error_source_missing", source_id=source_id)
            raise

    async def run_deterministic_mine(self, source_id: str) -> dict[str, Any]:
        """Run deterministic mining using existing runtime map."""
        runtime_map, runtime_map_source = await crud.get_active_runtime_map(self.db, source_id)
        if not crud.has_usable_runtime_map_payload(runtime_map):
            raise RuntimeError("Deterministic mining requires an active runtime map.")

        await self._report(
            stage="starting",
            item=source_id,
            message="Runtime mode selected: deterministic",
            event_type="runtime_mode_selected",
            metrics_payload={
                "runtime_mode": "deterministic",
                "runtime_map_source": runtime_map_source,
                "has_runtime_map": True,
            },
        )
        await crud.update_source(self.db, source_id, status="crawling")
        crawl_stats = await self.run_crawl(source_id)
        await self.db.commit()
        await crud.update_source(self.db, source_id, status="extracting")
        extract_stats = await self.run_extract(source_id, allow_updates=True, include_existing=False)
        await crud.update_source(
            self.db,
            source_id,
            status="done",
            last_crawled_at=datetime.now(UTC),
        )
        result = {
            "runtime_mode": "deterministic",
            "runtime_map_source": runtime_map_source,
            "records_created": extract_stats.records_created,
            "records_updated": extract_stats.records_updated,
            "records_failed": extract_stats.records_failed,
            "pages_processed": extract_stats.pages_processed,
            "deterministic_hits": extract_stats.deterministic_hits + int(crawl_stats.get("extracted_deterministic", 0)),
            "deterministic_misses": extract_stats.deterministic_misses + int(crawl_stats.get("failed", 0)),
            "media_assets_captured": extract_stats.media_assets_captured,
            "entity_links_created": extract_stats.entity_links_created,
        }
        await self._report(
            stage="finalizing",
            item=source_id,
            message="Deterministic mining completed",
            event_type="job_completed",
            progress_current=100,
            progress_total=100,
            metrics_payload=result,
        )
        return result

    async def run_enrichment_existing_pages(self, source_id: str) -> dict[str, Any]:
        """Enrichment-only run over stored page content; no recrawl."""
        runtime_map, runtime_map_source = await crud.get_active_runtime_map(self.db, source_id)
        if not crud.has_usable_runtime_map_payload(runtime_map):
            raise RuntimeError("Enrichment requires an active runtime map.")
        await self._report(
            stage="starting",
            item=source_id,
            message="Runtime mode selected: enrichment_only",
            event_type="runtime_mode_selected",
            metrics_payload={
                "runtime_mode": "enrichment_only",
                "runtime_map_source": runtime_map_source,
                "has_runtime_map": True,
            },
        )
        await crud.update_source(self.db, source_id, status="extracting")
        stats = await self.run_extract(source_id, allow_updates=True, include_existing=True)
        await crud.update_source(self.db, source_id, status="done")
        result = {
            "runtime_mode": "enrichment_only",
            "runtime_map_source": runtime_map_source,
            "records_created": stats.records_created,
            "records_updated": stats.records_updated,
            "records_failed": stats.records_failed,
            "pages_processed": stats.pages_processed,
            "deterministic_hits": stats.deterministic_hits,
            "deterministic_misses": stats.deterministic_misses,
            "media_assets_captured": stats.media_assets_captured,
            "entity_links_created": stats.entity_links_created,
        }
        await self._report(
            stage="finalizing",
            item=source_id,
            message="Enrichment completed",
            event_type="job_completed",
            progress_current=100,
            progress_total=100,
            metrics_payload=result,
        )
        return result

    async def run_reprocess_source_runtime_map(self, source_id: str) -> dict[str, Any]:
        """Reprocess all stored pages with current runtime map."""
        return await self.run_enrichment_existing_pages(source_id)

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

        runtime_map, runtime_map_source = await crud.get_active_runtime_map(self.db, source_id)
        if runtime_map is not None:
            structure_map = runtime_map

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
                    runtime_map_source=runtime_map_source,
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
            if settings.crawler_require_runtime_map:
                raise RuntimeError("Runtime map required for crawl but none exists.")

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

    async def run_extract(
        self,
        source_id: str,
        *,
        allow_updates: bool = False,
        include_existing: bool = False,
    ) -> ExtractionStats:
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
        statuses = ["fetched", "classified"]
        if include_existing:
            statuses.extend(["extracted", "expanded", "skipped"])
        pages = await crud.list_pages_by_statuses(
            self.db,
            source_id=source_id,
            statuses=statuses,
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
        total_pages = len(pages)
        await self._report(
            stage="extracting",
            item=source_id,
            message="Extraction loop started",
            progress_current=0,
            progress_total=total_pages,
            event_type="stage_changed",
        )

        for idx, page in enumerate(pages, start=1):
            await self._control_checkpoint()
            try:
                record, action = await self.run_extraction_for_page(
                    page,
                    structure_map=structure_map,
                    allow_updates=allow_updates,
                )
                if action == "created":
                    stats.records_created += 1
                elif action == "updated":
                    stats.records_updated += 1
                stats.deterministic_hits += int(record.get("deterministic_hit", 0)) if isinstance(record, dict) else 0
                stats.deterministic_misses += int(record.get("deterministic_miss", 0)) if isinstance(record, dict) else 0
                stats.media_assets_captured += int(record.get("media_assets_captured", 0)) if isinstance(record, dict) else 0
                stats.entity_links_created += int(record.get("entity_links_created", 0)) if isinstance(record, dict) else 0
                stats.pages_processed += 1
            except Exception as exc:
                logger.error("extract_page_error", page_id=page.id, error=str(exc))
                stats.records_failed += 1
            if idx == 1 or idx == total_pages or idx % 5 == 0:
                await self._report(
                    stage="extracting",
                    item=page.url,
                    message="Extraction progress",
                    progress_current=idx,
                    progress_total=total_pages,
                    metrics_payload={
                        "records_created": stats.records_created,
                        "records_updated": stats.records_updated,
                        "records_failed": stats.records_failed,
                        "pages_processed": stats.pages_processed,
                        "deterministic_hits": stats.deterministic_hits,
                        "deterministic_misses": stats.deterministic_misses,
                        "media_assets_captured": stats.media_assets_captured,
                        "entity_links_created": stats.entity_links_created,
                    },
                    event_type="progress",
                )

        logger.info(
            "pages_processed",
            source_id=source_id,
            pages_processed=stats.pages_processed,
            records_created=stats.records_created,
            records_updated=stats.records_updated,
            records_failed=stats.records_failed,
        )
        metrics.increment("pages_processed", stats.pages_processed)
        metrics.increment("records_created", stats.records_created)
        metrics.increment("records_updated", stats.records_updated)
        total_records = await crud.count_records(self.db, source_id=source_id)
        await crud.update_source(self.db, source_id, total_records=total_records)
        return stats

    async def run_extraction_for_page(
        self,
        page: Page,
        *,
        structure_map: dict[str, Any] | None = None,
        allow_updates: bool = False,
    ) -> tuple[dict[str, int], str | None]:
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
            return {}, None

        logger.info(
            "page_classified",
            source_id=page.source_id,
            page_id=page.id,
            url=page.url,
        )
        source_hints = await self._get_crawl_hints(page.source_id)
        if self._should_ignore_url(page.url, source_hints):
            await crud.update_page(self.db, page.id, status="skipped")
            return {}, None

        forced_page_type = self._get_page_role_override(page.url, source_hints)
        expected_fields: list[str] | None = None
        deterministic_hit = False
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
                deterministic_hit = True
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
                await self._report(
                    stage="extracting",
                    item=page.url,
                    message=f"Deterministic classification hit: {structured['page_type']}",
                    event_type="deterministic_classification_hit",
                )
            else:
                if self.ai_client is None:
                    classify_result = type(
                        "NoAIClassifyResult",
                        (),
                        {
                            "page_type": "unknown",
                            "confidence": 0,
                            "reasoning": "deterministic_rules_miss_ai_unavailable",
                        },
                    )()
                    await self._report(
                        stage="extracting",
                        item=page.url,
                        message="Deterministic classification miss; AI unavailable",
                        event_type="deterministic_extraction_miss",
                        level="warning",
                    )
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
            return {}, None

        if self._is_force_deepen(page.url, source_hints):
            await self.deepen_same_slug_children(page, source_hints=source_hints)

        if classify_result.page_type in ARTIST_RELATED_PAGE_TYPES:
            artist_record = await self.process_artist_related_page(
                page,
                classify_result.page_type,
                final_status="extracted",
            )
            if artist_record is None:
                return {}, None
            return {
                "deterministic_hit": 1 if deterministic_hit else 0,
                "deterministic_miss": 0 if deterministic_hit else 1,
                "media_assets_captured": 0,
                "entity_links_created": 0,
            }, "updated" if artist_record is not None else None

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
            return {}, None

        # Extract
        extractor = self._extractors.get(record_type)
        if extractor is None:
            await self._report(
                stage="extracting",
                item=page.url,
                message=f"Skipped page: no deterministic extractor and AI unavailable ({record_type})",
                event_type="page_skipped_no_runtime_rule",
                level="warning",
            )
            logger.warning(
                "page_extraction_skipped_missing_extractor",
                source_id=page.source_id,
                page_id=page.id,
                url=page.url,
                record_type=record_type,
            )
            return {}, None

        existing_record = await crud.get_record_by_page_and_type(
            self.db,
            source_id=page.source_id,
            page_id=page.id,
            record_type=record_type,
        )
        if existing_record is not None and not allow_updates:
            await crud.update_page(self.db, page.id, status="extracted", extracted_at=datetime.now(UTC))
            logger.info(
                "record_duplicate_skipped",
                source_id=page.source_id,
                page_id=page.id,
                record_id=existing_record.id,
                record_type=record_type,
            )
            metrics.increment("duplicate_items_skipped")
            return {}, None

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
            return {}, None

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

        action = "created"
        if existing_record is None:
            record = await crud.create_record(
                self.db,
                source_id=page.source_id,
                record_type=record_type,
                **record_kwargs,
            )
        else:
            record = await crud.update_record(self.db, existing_record.id, **record_kwargs)
            action = "updated"
        logger.info(
            "record_created",
            source_id=page.source_id,
            page_id=page.id,
            record_id=record.id,
            record_type=record_type,
            confidence_score=score,
            confidence_band=band,
        )
        metrics.increment("records_created" if action == "created" else "records_updated")

        await crud.update_page(
            self.db, page.id, status="extracted", extracted_at=datetime.now(UTC)
        )

        # Collect images
        media_assets_captured = 0
        try:
            collected_images = await collect_images(
                record_id=record.id,
                page_url=page.url,
                html=page.html,
                image_urls=image_urls,
                db=self.db,
                source_id=page.source_id,
                page_id=page.id,
            )
            media_assets_captured = len(collected_images)
        except Exception as exc:
            logger.warning("image_collection_error", record_id=record.id, error=str(exc))

        entity_links_created = await self._assemble_entity_relationships(record)
        return {
            "deterministic_hit": 1 if deterministic_hit else 0,
            "deterministic_miss": 0 if deterministic_hit else 1,
            "media_assets_captured": media_assets_captured,
            "entity_links_created": entity_links_created,
        }, action

    async def _assemble_entity_relationships(self, record: Record) -> int:
        created_links = 0
        if record.record_type in {"event", "exhibition"}:
            venue_name = (record.venue_name or "").strip()
            if venue_name:
                target = await self._find_record_by_title(
                    source_id=record.source_id,
                    record_type="venue",
                    title=venue_name,
                )
                if target is not None:
                    if await crud.ensure_entity_relationship(
                        self.db,
                        source_id=record.source_id,
                        from_record_id=record.id,
                        to_record_id=target.id,
                        relationship_type="event_venue",
                        metadata={"venue_name": venue_name},
                    ):
                        created_links += 1
            artist_names = self._parse_list_field(record.artist_names)
            for artist_name in artist_names:
                target = await self._find_record_by_title(
                    source_id=record.source_id,
                    record_type="artist",
                    title=artist_name,
                )
                if target is None:
                    continue
                if await crud.ensure_entity_relationship(
                    self.db,
                    source_id=record.source_id,
                    from_record_id=target.id,
                    to_record_id=record.id,
                    relationship_type="artist_event",
                    metadata={"artist_name": artist_name},
                ):
                    created_links += 1
        elif record.record_type == "venue":
            events = await crud.list_records(
                self.db,
                source_id=record.source_id,
                record_type="event",
                skip=0,
                limit=5000,
            )
            for event in events:
                if (event.venue_name or "").strip().lower() != (record.title or "").strip().lower():
                    continue
                if await crud.ensure_entity_relationship(
                    self.db,
                    source_id=record.source_id,
                    from_record_id=event.id,
                    to_record_id=record.id,
                    relationship_type="event_venue",
                    metadata={"venue_name": event.venue_name},
                ):
                    created_links += 1
        return created_links

    async def _find_record_by_title(self, *, source_id: str, record_type: str, title: str) -> Record | None:
        candidates = await crud.list_records(
            self.db,
            source_id=source_id,
            record_type=record_type,
            skip=0,
            limit=5000,
        )
        title_key = title.strip().lower()
        for candidate in candidates:
            if (candidate.title or "").strip().lower() == title_key:
                return candidate
        return None

    def _parse_list_field(self, raw_value: str | None) -> list[str]:
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            parsed = []
        if not isinstance(parsed, list):
            return []
        return [str(item).strip() for item in parsed if str(item).strip()]

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
            artist_extractor = self._extractors.get("artist")
            if artist_extractor is None:
                await self._report(
                    stage="extracting",
                    item=page.url,
                    message="Skipped artist extraction: AI unavailable and no deterministic extractor",
                    event_type="page_skipped_no_runtime_rule",
                    level="warning",
                )
                await crud.update_page(self.db, page.id, status="skipped")
                return None
            try:
                extracted_data = await artist_extractor.extract(url=page.url, html=page.html or "")
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
        runtime_map, _runtime_map_source = await crud.get_active_runtime_map(self.db, source_id)
        return runtime_map

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
            await crud.heartbeat_worker(
                db,
                worker_id=WORKER_ID,
                status="idle",
                current_job_id=None,
                current_stage=None,
            )
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

            ai_client: OpenAIClient | None = None
            if settings.crawler_allow_ai and settings.openai_api_key:
                ai_client = OpenAIClient()
            runner = PipelineRunner(db=db, ai_client=ai_client, job_id=job_id, source_id=source_id)
            try:
                claimed = await crud.claim_job_for_worker(
                    db,
                    job_id=job_id,
                    worker_id=WORKER_ID,
                    max_concurrent_jobs=MAX_CONCURRENT_JOBS,
                )
                if claimed is None:
                    logger.info(
                        "pipeline_job_concurrency_gate_blocked",
                        job_id=job_id,
                        worker_id=WORKER_ID,
                        max_concurrent_jobs=MAX_CONCURRENT_JOBS,
                    )
                    current = await crud.get_job(db, job_id)
                    if current is not None and current.status in {"queued", "pending"}:
                        try:
                            queue = get_default_queue()
                            queue.enqueue(
                                "app.pipeline.runner.process_pipeline_job",
                                job_id,
                                source_id,
                                job_type,
                                {},
                            )
                        except QueueUnavailableError:
                            logger.warning("pipeline_job_requeue_unavailable", job_id=job_id)
                    return
                await crud.heartbeat_worker(
                    db,
                    worker_id=WORKER_ID,
                    status="running",
                    current_job_id=job_id,
                    current_stage="starting",
                )
                await report_job_progress(
                    db,
                    job_id,
                    source_id=source_id,
                    worker_id=WORKER_ID,
                    stage="starting",
                    item=source_id,
                    message=f"Job started ({job_type})",
                    progress_current=0,
                    progress_total=100,
                    event_type="job_started",
                )
            except ValueError:
                logger.error("pipeline_job_missing_job_row_on_start", job_id=job_id, source_id=source_id)
                return

            try:
                if job_type == "run_full_pipeline":
                    await runner.run_full_pipeline(source_id)
                    result = {"status": "done"}
                elif job_type == "mine_source_deterministic":
                    result = await runner.run_deterministic_mine(source_id)
                elif job_type == "enrich_source_existing_pages":
                    result = await runner.run_enrichment_existing_pages(source_id)
                elif job_type == "reprocess_source_runtime_map":
                    result = await runner.run_reprocess_source_runtime_map(source_id)
                elif job_type == "map_site":
                    site_map = await runner.run_map_site(source_id)
                    result = {"sections": len(site_map.sections)}
                elif job_type == "crawl_section":
                    result = await runner.run_crawl(source_id)
                elif job_type == "extract_page":
                    stats = await runner.run_extract(source_id, allow_updates=False, include_existing=False)
                    result = {
                        "runtime_mode": "extract_only",
                        "records_created": stats.records_created,
                        "records_updated": stats.records_updated,
                        "records_failed": stats.records_failed,
                        "pages_processed": stats.pages_processed,
                        "deterministic_hits": stats.deterministic_hits,
                        "deterministic_misses": stats.deterministic_misses,
                        "media_assets_captured": stats.media_assets_captured,
                        "entity_links_created": stats.entity_links_created,
                    }
                else:
                    raise ValueError(f"Unsupported job type: {job_type}")

                await crud.update_job_status(
                    db,
                    job_id,
                    "done",
                    result=result,
                    completed_at=datetime.now(UTC),
                    worker_id=WORKER_ID,
                )
                await report_job_progress(
                    db,
                    job_id,
                    source_id=source_id,
                    worker_id=WORKER_ID,
                    stage="finalizing",
                    item=source_id,
                    message="Job completed",
                    progress_current=100,
                    progress_total=100,
                    metrics=result if isinstance(result, dict) else None,
                    event_type="job_completed",
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
                        worker_id=WORKER_ID,
                    )
                    await report_job_progress(
                        db,
                        job_id,
                        source_id=source_id,
                        worker_id=WORKER_ID,
                        stage="finalizing",
                        item=source_id,
                        message=f"Job failed: {exc}",
                        event_type="job_failed",
                        level="error",
                    )
                except ValueError:
                    logger.warning(
                        "pipeline_job_failed_status_update_skipped",
                        job_id=job_id,
                        source_id=source_id,
                    )
                raise
            finally:
                await crud.heartbeat_worker(
                    db,
                    worker_id=WORKER_ID,
                    status="idle",
                    current_job_id=None,
                    current_stage=None,
                )
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
    worker = Worker(["default"], connection=redis_conn, name=WORKER_ID)
    worker.work()


if __name__ == "__main__":
    main()
