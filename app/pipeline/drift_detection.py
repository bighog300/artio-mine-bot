from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import Page, Record, Source
from app.services.completeness import RECORD_TYPE_FIELDS

logger = structlog.get_logger()


@dataclass(frozen=True)
class DriftConfig:
    severe_drift_rate_threshold: float = 0.2
    confidence_drop_threshold: int = 25
    numeric_deviation_multiplier: float = 2.5
    text_length_ratio_threshold: float = 0.5


class DriftDetectionService:
    def __init__(self, db: AsyncSession, *, config: DriftConfig | None = None) -> None:
        self.db = db
        self.config = config or DriftConfig()

    async def analyze_source(self, source_id: str, *, page_ids: list[str] | None = None) -> dict[str, Any]:
        source = await crud.get_source(self.db, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")

        mapping_version_id = source.published_mapping_version_id or source.active_mapping_version_id

        pages_stmt = select(Page).where(Page.source_id == source_id)
        if mapping_version_id:
            pages_stmt = pages_stmt.where(Page.mapping_version_id_used == mapping_version_id)
        if page_ids:
            pages_stmt = pages_stmt.where(Page.id.in_(page_ids))
        pages = list((await self.db.execute(pages_stmt)).scalars().all())

        emitted: list[str] = []
        fields_counter: Counter[str] = Counter()
        severity_counter: Counter[str] = Counter()
        pages_with_drift: set[str] = set()

        for page in pages:
            record = await self._latest_record_for_page(page)
            if record is None:
                continue
            signals = await self._analyze_page_record(source, page, record, mapping_version_id)
            if signals:
                pages_with_drift.add(page.id)
            for signal in signals:
                emitted.append(signal.id)
                if signal.field_name:
                    fields_counter[signal.field_name] += 1
                severity_counter[signal.severity.lower()] += 1

        total_pages_checked = len(pages)
        drift_rate = (len(pages_with_drift) / total_pages_checked) if total_pages_checked else 0.0
        alert_level = "high" if drift_rate > self.config.severe_drift_rate_threshold else "normal"
        if alert_level == "high":
            await crud.update_source(
                self.db,
                source_id,
                queue_paused=True,
                status="paused",
                mapping_status="degraded",
                mapping_stale=True,
                health_status="degraded",
            )

        return {
            "source_id": source_id,
            "mapping_version_id": mapping_version_id,
            "total_pages_checked": total_pages_checked,
            "pages_with_drift": len(pages_with_drift),
            "drift_rate": round(drift_rate * 100, 2),
            "top_failing_fields": [{"field": k, "count": v} for k, v in fields_counter.most_common(10)],
            "severity_distribution": dict(severity_counter),
            "alert_level": alert_level,
            "signal_ids": emitted,
        }

    async def _latest_record_for_page(self, page: Page) -> Record | None:
        result = await self.db.execute(
            select(Record)
            .where(Record.source_id == page.source_id, Record.page_id == page.id)
            .order_by(Record.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _analyze_page_record(
        self,
        source: Source,
        page: Page,
        record: Record,
        mapping_version_id: str | None,
    ) -> list[Any]:
        baseline_row = await crud.get_extraction_baseline(self.db, source_id=source.id, page_id=page.id)
        baseline = json.loads(baseline_row.baseline_json) if baseline_row else {}
        stats = json.loads(baseline_row.field_stats_json) if baseline_row else {}

        signals: list[Any] = []
        fields_cfg = RECORD_TYPE_FIELDS.get(record.record_type, {"critical": ["title", "source_url"], "important": [], "optional": []})
        check_fields = fields_cfg["critical"] + fields_cfg["important"]

        current_values = {f: getattr(record, f, None) for f in set(check_fields + ["title", "description", "start_date", "end_date", "venue_name", "year", "birth_year"]) }

        for field in check_fields:
            prev = baseline.get(field)
            current = current_values.get(field)
            missing_now = current is None
            empty_now = isinstance(current, str) and not current.strip()
            had_prev = prev is not None and (not isinstance(prev, str) or prev.strip())

            if had_prev and missing_now:
                signals.append(
                    await crud.create_mapping_drift_signal(
                        self.db,
                        source_id=source.id,
                        mapping_version_id=mapping_version_id,
                        page_id=page.id,
                        record_id=record.id,
                        field_name=field,
                        drift_type="FIELD_MISSING",
                        signal_type="field_missing",
                        severity="high",
                        previous_value=str(prev),
                        current_value=None,
                        confidence=0.95,
                        sample_urls=[page.url],
                        metrics={"rule": "previous_present_current_missing"},
                    )
                )
                continue

            if had_prev and empty_now:
                signals.append(
                    await crud.create_mapping_drift_signal(
                        self.db,
                        source_id=source.id,
                        mapping_version_id=mapping_version_id,
                        page_id=page.id,
                        record_id=record.id,
                        field_name=field,
                        drift_type="FIELD_EMPTY",
                        signal_type="field_empty",
                        severity="high",
                        previous_value=str(prev),
                        current_value=str(current),
                        confidence=0.95,
                        sample_urls=[page.url],
                        metrics={"rule": "previous_non_empty_current_empty"},
                    )
                )
                continue

            anomaly = self._value_anomaly(field, prev, current, stats.get(field, {}))
            if anomaly is not None:
                signals.append(
                    await crud.create_mapping_drift_signal(
                        self.db,
                        source_id=source.id,
                        mapping_version_id=mapping_version_id,
                        page_id=page.id,
                        record_id=record.id,
                        field_name=field,
                        drift_type="VALUE_ANOMALY",
                        signal_type="value_anomaly",
                        severity=anomaly["severity"],
                        previous_value=str(prev) if prev is not None else None,
                        current_value=str(current) if current is not None else None,
                        confidence=anomaly["confidence"],
                        sample_urls=[page.url],
                        metrics=anomaly,
                    )
                )

        if page.error_message and "selector" in page.error_message.lower():
            signals.append(
                await crud.create_mapping_drift_signal(
                    self.db,
                    source_id=source.id,
                    mapping_version_id=mapping_version_id,
                    page_id=page.id,
                    record_id=record.id,
                    drift_type="SELECTOR_FAIL",
                    signal_type="selector_fail",
                    severity="high",
                    confidence=0.92,
                    current_value=page.error_message,
                    sample_urls=[page.url],
                )
            )

        old_hash = baseline_row.dom_section_hash if baseline_row else None
        new_hash = page.template_hash or page.content_hash
        if old_hash and new_hash and old_hash != new_hash:
            signals.append(
                await crud.create_mapping_drift_signal(
                    self.db,
                    source_id=source.id,
                    mapping_version_id=mapping_version_id,
                    page_id=page.id,
                    record_id=record.id,
                    drift_type="STRUCTURE_CHANGED",
                    signal_type="structure_changed",
                    severity="medium",
                    previous_value=old_hash,
                    current_value=new_hash,
                    confidence=0.85,
                    sample_urls=[page.url],
                )
            )

        if baseline_row and baseline_row.confidence_score is not None:
            drop = baseline_row.confidence_score - int(record.confidence_score or 0)
            if drop >= self.config.confidence_drop_threshold:
                signals.append(
                    await crud.create_mapping_drift_signal(
                        self.db,
                        source_id=source.id,
                        mapping_version_id=mapping_version_id,
                        page_id=page.id,
                        record_id=record.id,
                        drift_type="VALUE_ANOMALY",
                        signal_type="confidence_drop",
                        severity="medium",
                        previous_value=str(baseline_row.confidence_score),
                        current_value=str(record.confidence_score),
                        confidence=0.8,
                        sample_urls=[page.url],
                        metrics={"confidence_drop": drop, "threshold": self.config.confidence_drop_threshold},
                    )
                )

        next_stats = self._update_field_stats(stats, current_values)
        await crud.upsert_extraction_baseline(
            self.db,
            source_id=source.id,
            page_id=page.id,
            mapping_version_id=mapping_version_id,
            record_id=record.id,
            baseline=current_values,
            field_stats=next_stats,
            dom_section_hash=new_hash,
            confidence_score=int(record.confidence_score or 0),
        )
        return signals

    def _value_anomaly(self, field: str, previous: Any, current: Any, stats: dict[str, Any]) -> dict[str, Any] | None:
        if previous is None or current is None:
            return None
        if isinstance(current, (int, float)) and isinstance(previous, (int, float)):
            avg = float(stats.get("mean", previous))
            std = float(stats.get("std", 0.0))
            diff = abs(float(current) - avg)
            threshold = max(std * self.config.numeric_deviation_multiplier, 1.0)
            if diff > threshold:
                return {"severity": "medium", "confidence": 0.8, "difference": diff, "threshold": threshold}
            return None

        if field.endswith("date") and isinstance(current, str) and isinstance(previous, str):
            if current[:7] != previous[:7]:
                return {"severity": "low", "confidence": 0.6, "kind": "date_pattern_change"}
            return None

        if isinstance(current, str) and isinstance(previous, str):
            prev_len = max(len(previous.strip()), 1)
            cur_len = len(current.strip())
            ratio = abs(cur_len - prev_len) / prev_len
            if ratio >= self.config.text_length_ratio_threshold:
                severity = "medium" if ratio >= 1.0 else "low"
                return {"severity": severity, "confidence": 0.7, "length_ratio_delta": round(ratio, 4)}
            prev_digits = bool(re.search(r"\d", previous))
            cur_digits = bool(re.search(r"\d", current))
            if prev_digits != cur_digits:
                return {"severity": "low", "confidence": 0.65, "kind": "text_pattern_changed"}
        return None

    def _update_field_stats(self, stats: dict[str, Any], current_values: dict[str, Any]) -> dict[str, Any]:
        updated = dict(stats)
        for field, value in current_values.items():
            bucket = dict(updated.get(field, {}))
            count = int(bucket.get("count", 0)) + 1
            bucket["count"] = count
            if isinstance(value, (int, float)):
                mean = float(bucket.get("mean", float(value)))
                delta = float(value) - mean
                mean = mean + (delta / count)
                var = float(bucket.get("var", 0.0))
                var = var + delta * (float(value) - mean)
                bucket["mean"] = mean
                bucket["var"] = var
                bucket["std"] = (var / max(count - 1, 1)) ** 0.5
            elif isinstance(value, str):
                mean = float(bucket.get("len_mean", len(value)))
                delta = len(value) - mean
                bucket["len_mean"] = mean + delta / count
            updated[field] = bucket
        return updated
