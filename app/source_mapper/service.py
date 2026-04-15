import json
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import Source, SourceMappingSample, SourceMappingVersion
from app.source_mapper.page_clustering import cluster_pages
from app.source_mapper.proposal_engine import build_proposals
from app.source_mapper.preview import build_preview
from app.source_mapper.types import DiscoveredPage

logger = structlog.get_logger()


class SourceMapperService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_scan(self, source: Source, draft: SourceMappingVersion) -> dict[str, int | str]:
        try:
            draft.scan_status = "running"
            source.mapping_status = "draft"
            await self.db.commit()

            discovered_pages = self._build_discovery_seed(source)
            clusters = cluster_pages(discovered_pages)

            for cluster in clusters:
                page_type = await crud.create_source_mapping_page_type(
                    self.db,
                    draft.id,
                    key=cluster.key,
                    label=cluster.label,
                    sample_count=len(cluster.sample_urls),
                    confidence_score=cluster.confidence_score,
                )
                for sample_url in cluster.sample_urls:
                    await crud.create_source_mapping_sample(
                        self.db,
                        draft.id,
                        page_type_id=page_type.id,
                        url=sample_url,
                        title=source.name,
                        html_snapshot=None,
                    )

                proposals = build_proposals(cluster, source_name=source.name)
                for proposal in proposals:
                    await crud.create_source_mapping_row(
                        self.db,
                        draft.id,
                        page_type_id=page_type.id,
                        selector=proposal.selector,
                        sample_value=proposal.sample_value,
                        destination_entity=proposal.destination_entity,
                        destination_field=proposal.destination_field,
                        confidence_score=proposal.confidence_score,
                        status="proposed",
                        rationale=proposal.rationale,
                    )

            draft.scan_status = "completed"
            source.last_mapping_scan_at = datetime.now(UTC)
            source.last_mapping_error = None
            await self.db.commit()
            return {"scan_status": draft.scan_status, "page_type_count": len(clusters)}
        except Exception as exc:
            logger.exception(
                "source_mapper_scan_failed",
                source_id=source.id,
                draft_id=draft.id,
                error=str(exc),
            )
            draft.scan_status = "error"
            source.mapping_status = "error"
            source.last_mapping_error = str(exc)
            await self.db.commit()
            return {"scan_status": "error", "error": str(exc), "page_type_count": 0}

    async def generate_preview(self, source_id: str, draft_id: str, sample_page_id: str) -> dict:
        sample = await self._resolve_sample(draft_id, sample_page_id)
        if sample is None:
            raise ValueError("Sample page not found")

        rows = await crud.list_source_mapping_rows(self.db, source_id, draft_id, skip=0, limit=1_000)
        extractions, record_preview, category_preview, warnings, source_snippet = build_preview(
            rows,
            sample,
            low_confidence_threshold=0.65,
        )

        sample_run = await crud.create_source_mapping_sample_run(
            self.db,
            draft_id,
            sample_count=1,
            created_by="admin",
            summary={"sample_page_id": sample.id, "extraction_count": len(extractions)},
        )
        await crud.create_source_mapping_sample_result(
            self.db,
            sample_run.id,
            sample_id=sample.id,
            record_preview={"record_preview": record_preview, "extractions": extractions, "warnings": warnings},
        )

        return {
            "sample_page_id": sample.id,
            "page_url": sample.url,
            "page_type_key": sample.page_type.key if sample.page_type else None,
            "extractions": extractions,
            "record_preview": record_preview,
            "source_snippet": source_snippet,
            "category_preview": category_preview,
            "warnings": warnings,
        }

    async def run_sample_review(
        self,
        source_id: str,
        draft_id: str,
        *,
        sample_count: int,
        page_type_keys: list[str] | None = None,
    ) -> dict[str, str]:
        rows = await crud.list_source_mapping_rows(self.db, source_id, draft_id, skip=0, limit=2_000)
        samples = await self._list_samples_for_draft(draft_id)
        if page_type_keys:
            samples = [
                sample
                for sample in samples
                if sample.page_type is not None and sample.page_type.key in set(page_type_keys)
            ]
        selected = samples[:sample_count]

        run = await crud.create_source_mapping_sample_run(
            self.db,
            draft_id,
            sample_count=len(selected),
            created_by="admin",
            status="running",
            summary={"page_type_keys": page_type_keys or [], "requested": sample_count},
        )
        for sample in selected:
            extractions, record_preview, _, warnings, _ = build_preview(rows, sample, low_confidence_threshold=0.65)
            await crud.create_source_mapping_sample_result(
                self.db,
                run.id,
                sample_id=sample.id,
                record_preview={
                    "page_url": sample.url,
                    "record_preview": record_preview,
                    "extractions": extractions,
                    "warnings": warnings,
                },
                review_status="pending",
            )

        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        run.summary_json = json.dumps({"processed": len(selected), "warnings": sum(1 for _ in selected)})
        await self.db.commit()
        return {"sample_run_id": run.id, "status": run.status}

    def _build_discovery_seed(self, source: Source) -> list[DiscoveredPage]:
        base = source.url.rstrip("/")
        return [
            DiscoveredPage(url=base, title=source.name),
            DiscoveredPage(url=f"{base}/events/sample-event", title="Sample Event"),
            DiscoveredPage(url=f"{base}/artists/sample-artist", title="Sample Artist"),
            DiscoveredPage(url=f"{base}/exhibitions/sample-exhibition", title="Sample Exhibition"),
            DiscoveredPage(url=f"{base}/venues/sample-venue", title="Sample Venue"),
        ]

    async def _resolve_sample(self, draft_id: str, sample_page_id: str) -> SourceMappingSample | None:
        if sample_page_id == "default":
            result = await self.db.execute(
                select(SourceMappingSample).where(SourceMappingSample.mapping_version_id == draft_id)
            )
            return result.scalars().first()
        return await crud.get_source_mapping_sample(self.db, sample_page_id)

    async def _list_samples_for_draft(self, draft_id: str) -> list[SourceMappingSample]:
        result = await self.db.execute(
            select(SourceMappingSample).where(SourceMappingSample.mapping_version_id == draft_id)
        )
        return list(result.scalars().all())
