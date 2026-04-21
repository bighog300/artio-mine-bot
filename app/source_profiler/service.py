from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import Source
from app.source_profiler.clustering import cluster_profiled_pages
from app.source_profiler.discovery import discover_site_pages

logger = structlog.get_logger()


class SourceProfilerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def profile_source(self, source: Source, *, max_pages: int = 40) -> tuple[object, list[object]]:
        profile = await crud.create_source_profile(self.db, source_id=source.id, seed_url=source.url)
        try:
            entrypoints, pages, discovery_meta = await discover_site_pages(source.url, max_pages=max_pages)
            families = cluster_profiled_pages(pages)

            fingerprint = {
                "host": source.url.split("//")[-1].split("/")[0].lower(),
                "scheme": "https" if source.url.lower().startswith("https://") else "http",
                "sampled_page_count": len(pages),
            }
            metrics = {
                "entrypoints_count": len(entrypoints),
                "families_count": len(families),
                "sampled_at": datetime.now(UTC).isoformat(),
            }
            await crud.finalize_source_profile(
                self.db,
                profile.id,
                status="completed",
                site_fingerprint=fingerprint,
                sitemap_urls=discovery_meta.get("sitemap_urls", []),
                nav_discovery_summary={
                    "entrypoints": entrypoints[:12],
                    "nav_links_count": discovery_meta.get("nav_links_count", 0),
                },
                profile_metrics=metrics,
            )
            saved_families = await crud.replace_url_families(
                self.db,
                profile_id=profile.id,
                families=[
                    {
                        "family_key": cluster.family_key,
                        "family_label": cluster.family_label,
                        "path_pattern": cluster.path_pattern,
                        "page_type_candidate": cluster.page_type_candidate,
                        "confidence": cluster.confidence,
                        "sample_urls": cluster.sample_urls,
                        "follow_policy_candidate": "follow_if_internal",
                        "pagination_policy_candidate": "auto_detect",
                        "include_by_default": cluster.page_type_candidate != "utility",
                        "diagnostics": cluster.diagnostics,
                    }
                    for cluster in families
                ],
            )
            return profile, saved_families
        except (ValueError, RuntimeError, TypeError) as exc:
            logger.exception("source_profiling_failed", source_id=source.id, profile_id=profile.id, error=str(exc))
            await crud.finalize_source_profile(
                self.db,
                profile.id,
                status="error",
                site_fingerprint={},
                sitemap_urls=[],
                nav_discovery_summary={},
                profile_metrics={"error": str(exc)},
            )
            raise
