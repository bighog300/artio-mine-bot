from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import CrawlFrontier, Page

logger = structlog.get_logger()


@dataclass(frozen=True)
class DriftThresholds:
    min_family_volume: int = 8
    null_rate_warn: float = 0.35
    null_rate_stale: float = 0.55
    refresh_change_warn: float = 0.45
    refresh_change_stale: float = 0.7
    unexpected_skip_warn: float = 0.2
    unexpected_skip_stale: float = 0.35
    new_family_min_count: int = 5


class DriftDetectionService:
    """Deterministic drift signal emitter for approved mappings."""

    def __init__(self, db: AsyncSession, *, thresholds: DriftThresholds | None = None) -> None:
        self.db = db
        self.thresholds = thresholds or DriftThresholds()

    async def detect_for_source(self, source_id: str) -> dict[str, Any]:
        source = await crud.get_source(self.db, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")
        mapping_version_id = source.published_mapping_version_id or source.active_mapping_version_id
        if mapping_version_id is None:
            return {"source_id": source_id, "mapping_version_id": None, "created": 0, "signals": []}

        mapping = await crud.get_source_mapping_version(self.db, source_id, mapping_version_id)
        if mapping is None:
            return {"source_id": source_id, "mapping_version_id": mapping_version_id, "created": 0, "signals": []}

        mapping_json = json.loads(mapping.mapping_json or "{}")
        covered_families = {
            str(rule.get("family_key"))
            for rule in mapping_json.get("family_rules", [])
            if isinstance(rule, dict) and rule.get("family_key") and rule.get("include", True)
        }

        frontier_rows = list(
            (
                await self.db.execute(
                    select(CrawlFrontier).where(
                        CrawlFrontier.source_id == source_id,
                        CrawlFrontier.mapping_version_id == mapping_version_id,
                    )
                )
            ).scalars().all()
        )

        by_family: dict[str, list[CrawlFrontier]] = {}
        for row in frontier_rows:
            family = row.family_key or "__unknown__"
            by_family.setdefault(family, []).append(row)

        created_signals = []
        for family_key, family_rows in by_family.items():
            emitted = await self._detect_family_signals(
                source_id=source_id,
                mapping_version_id=mapping_version_id,
                family_key=family_key,
                rows=family_rows,
            )
            created_signals.extend(emitted)

        # New recurring family not in active mapping coverage.
        for family_key, family_rows in by_family.items():
            if family_key == "__unknown__" or family_key in covered_families:
                continue
            if len(family_rows) < self.thresholds.new_family_min_count:
                continue
            sample_urls = [row.url for row in family_rows[:5] if row.url]
            signal = await crud.create_mapping_drift_signal(
                self.db,
                source_id=source_id,
                mapping_version_id=mapping_version_id,
                family_key=family_key,
                signal_type="new_unmapped_family",
                severity="medium",
                metrics={"count": len(family_rows), "new_family_threshold": self.thresholds.new_family_min_count},
                diagnostics={"reason": "family_not_covered_by_mapping_rules"},
                sample_urls=sample_urls,
                proposed_action="Generate remap draft and review family coverage",
            )
            created_signals.append(signal)

        health = await crud.get_mapping_health_state(
            self.db,
            source_id=source_id,
            mapping_version_id=mapping_version_id,
        )
        await crud.update_source(
            self.db,
            source_id,
            mapping_stale=(health == "stale"),
            mapping_status=health,
        )

        logger.info(
            "drift_detection_completed",
            source_id=source_id,
            mapping_version_id=mapping_version_id,
            signal_count=len(created_signals),
            mapping_health=health,
        )
        return {
            "source_id": source_id,
            "mapping_version_id": mapping_version_id,
            "created": len(created_signals),
            "signals": [signal.id for signal in created_signals],
            "mapping_health": health,
        }

    async def _detect_family_signals(
        self,
        *,
        source_id: str,
        mapping_version_id: str,
        family_key: str,
        rows: list[CrawlFrontier],
    ) -> list[Any]:
        emitted: list[Any] = []
        total = len(rows)
        if total < self.thresholds.min_family_volume:
            return emitted

        sample_urls = [row.url for row in rows[:5] if row.url]

        selector_miss_count = sum(
            1
            for row in rows
            if row.skip_reason in {"selector_miss", "unmapped_page_type", "low_confidence_extraction"}
            or (row.last_error and "selector" in row.last_error.lower())
        )
        null_rate = selector_miss_count / max(total, 1)
        if null_rate >= self.thresholds.null_rate_warn:
            severity = "high" if null_rate >= self.thresholds.null_rate_stale else "medium"
            emitted.append(
                await crud.create_mapping_drift_signal(
                    self.db,
                    source_id=source_id,
                    mapping_version_id=mapping_version_id,
                    family_key=family_key,
                    signal_type="null_rate_spike",
                    severity=severity,
                    metrics={
                        "family_total": total,
                        "selector_like_miss_count": selector_miss_count,
                        "null_rate": round(null_rate, 4),
                        "warn_threshold": self.thresholds.null_rate_warn,
                        "stale_threshold": self.thresholds.null_rate_stale,
                    },
                    diagnostics={"reason": "selector_like_miss_rate_spike"},
                    sample_urls=sample_urls,
                    proposed_action="Review selectors and sample extraction output for this family",
                )
            )

        changed = [row for row in rows if row.last_refresh_outcome in {"changed", "unchanged"}]
        if changed:
            changed_count = sum(1 for row in changed if row.last_refresh_outcome == "changed")
            ratio = changed_count / max(len(changed), 1)
            if ratio >= self.thresholds.refresh_change_warn:
                severity = "high" if ratio >= self.thresholds.refresh_change_stale else "medium"
                emitted.append(
                    await crud.create_mapping_drift_signal(
                        self.db,
                        source_id=source_id,
                        mapping_version_id=mapping_version_id,
                        family_key=family_key,
                        signal_type="refresh_change_spike",
                        severity=severity,
                        metrics={
                            "observed_refreshes": len(changed),
                            "changed_pages": changed_count,
                            "change_ratio": round(ratio, 4),
                            "warn_threshold": self.thresholds.refresh_change_warn,
                            "stale_threshold": self.thresholds.refresh_change_stale,
                        },
                        diagnostics={"reason": "refresh_changed_ratio_spike"},
                        sample_urls=sample_urls,
                        proposed_action="Validate whether template/content structure changed for this family",
                    )
                )

        unexpected_skips = [row for row in rows if row.status == "skipped" and (row.skip_reason or "") not in {"robots_blocked", "max_depth_exceeded"}]
        if unexpected_skips:
            skip_ratio = len(unexpected_skips) / max(total, 1)
            if skip_ratio >= self.thresholds.unexpected_skip_warn:
                severity = "high" if skip_ratio >= self.thresholds.unexpected_skip_stale else "medium"
                emitted.append(
                    await crud.create_mapping_drift_signal(
                        self.db,
                        source_id=source_id,
                        mapping_version_id=mapping_version_id,
                        family_key=family_key,
                        signal_type="unexpected_skip_spike",
                        severity=severity,
                        metrics={
                            "family_total": total,
                            "unexpected_skip_count": len(unexpected_skips),
                            "skip_ratio": round(skip_ratio, 4),
                        },
                        diagnostics={
                            "reason": "unexpected_skip_reasons",
                            "sample_skip_reasons": sorted({row.skip_reason for row in unexpected_skips if row.skip_reason})[:5],
                        },
                        sample_urls=[row.url for row in unexpected_skips[:5] if row.url],
                        proposed_action="Review crawl family routing and skip diagnostics",
                    )
                )

        page_stmt = select(Page).where(
            Page.source_id == source_id,
            Page.mapping_version_id_used == mapping_version_id,
            Page.review_reason.in_(["selector_miss", "unmapped_page_type"]),
        )
        pages = list((await self.db.execute(page_stmt)).scalars().all())
        if pages and family_key != "__unknown__":
            matching_pages = [p for p in pages if family_key in (p.url or "")]
            if len(matching_pages) >= self.thresholds.new_family_min_count:
                emitted.append(
                    await crud.create_mapping_drift_signal(
                        self.db,
                        source_id=source_id,
                        mapping_version_id=mapping_version_id,
                        family_key=family_key,
                        signal_type="selector_like_miss",
                        severity="medium",
                        metrics={"count": len(matching_pages)},
                        diagnostics={"reason": "page_review_reason_selector_or_unmapped"},
                        sample_urls=[p.url for p in matching_pages[:5] if p.url],
                        proposed_action="Generate remap draft to refresh selectors for this family",
                    )
                )

        return emitted
