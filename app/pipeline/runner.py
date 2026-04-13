import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
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
from app.crawler.link_follower import crawl_source
from app.crawler.robots import RobotsChecker
from app.crawler.site_mapper import SiteMap, Section, map_site
from app.config import settings
from app.db import crud
from app.db.models import Page, Record
from app.pipeline.image_collector import collect_images
from app.pipeline.queue import PipelineQueue

logger = structlog.get_logger()

# Map page_type to record_type for detail pages
DETAIL_PAGE_TYPES = {
    "artist_profile": "artist",
    "event_detail": "event",
    "exhibition_detail": "exhibition",
    "venue_profile": "venue",
    "artwork_detail": "artwork",
}


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
        self.queue = PipelineQueue()
        self.robots_checker = RobotsChecker()
        self._extractors = {
            "artist": ArtistExtractor(ai_client),
            "event": EventExtractor(ai_client),
            "exhibition": ExhibitionExtractor(ai_client),
            "venue": VenueExtractor(ai_client),
            "artwork": ArtworkExtractor(ai_client),
        }

    async def run_full_pipeline(self, source_id: str) -> None:
        """Run complete pipeline: map → crawl → extract."""
        if settings.environment == "production":
            raise RuntimeError("This task must run in a worker environment, not Vercel.")
        try:
            await crud.update_source(self.db, source_id, status="mapping")
            site_map = await self.run_map_site(source_id)

            await crud.update_source(self.db, source_id, status="crawling")
            await self.run_crawl(source_id, site_map=site_map)

            await crud.update_source(self.db, source_id, status="extracting")
            await self.run_extract(source_id)

            await crud.update_source(
                self.db,
                source_id,
                status="done",
                last_crawled_at=datetime.now(UTC),
            )
            logger.info("pipeline_complete", source_id=source_id)
        except Exception as exc:
            logger.error("pipeline_error", source_id=source_id, error=str(exc))
            await crud.update_source(
                self.db, source_id, status="error", error_message=str(exc)
            )

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
        if site_map is None:
            source = await crud.get_source(self.db, source_id)
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
        return {"pages_fetched": stats.pages_fetched, "errors": stats.pages_error}

    async def run_extract(self, source_id: str) -> ExtractionStats:
        """Extract records from all fetched pages."""
        if settings.environment == "production":
            raise RuntimeError("This task must run in a worker environment, not Vercel.")
        pages = await crud.list_pages(
            self.db, source_id=source_id, status="fetched", limit=10000
        )
        stats = ExtractionStats()

        for page in pages:
            try:
                record = await self.run_extraction_for_page(page)
                if record:
                    stats.records_created += 1
                stats.pages_processed += 1
            except Exception as exc:
                logger.error("extract_page_error", page_id=page.id, error=str(exc))
                stats.records_failed += 1

        await crud.update_source(self.db, source_id, total_records=stats.records_created)
        return stats

    async def run_extraction_for_page(self, page: Page) -> Record | None:
        """Classify page, extract record, score confidence, store in DB."""
        if settings.environment == "production":
            raise RuntimeError("This task must run in a worker environment, not Vercel.")
        if not page.html:
            return None

        # Classify page
        classify_result = await classify_page(
            url=page.url, html=page.html, ai_client=self.ai_client
        )
        await crud.update_page(
            self.db, page.id, page_type=classify_result.page_type, status="classified"
        )

        record_type = DETAIL_PAGE_TYPES.get(classify_result.page_type)
        if record_type is None:
            # Not a detail page — skip extraction
            await crud.update_page(self.db, page.id, status="skipped")
            return None

        # Extract
        extractor = self._extractors.get(record_type)
        if extractor is None:
            return None

        try:
            data = await extractor.extract(url=page.url, html=page.html)
        except Exception as exc:
            logger.error("extractor_error", page_id=page.id, record_type=record_type, error=str(exc))
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
