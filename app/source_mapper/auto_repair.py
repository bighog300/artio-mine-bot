from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any

import structlog
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import MappingDriftSignal, Page, SourceMappingRow

logger = structlog.get_logger()


@dataclass(frozen=True)
class MappingRepairProposal:
    source_id: str
    mapping_version_id: str | None
    field_name: str
    old_selector: str | None
    proposed_selector: str
    confidence_score: float
    supporting_pages: list[str]
    drift_signals_used: list[str]
    validation_results: dict[str, Any]
    occurrence_count: int = 1
    priority_score: float = 0.0
    strategy_used: str = "selector_recovery"
    reasoning: str = ""
    evidence: dict[str, Any] | None = None
    status: str = "DRAFT"


class AutoRepairService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_for_signal(self, signal: MappingDriftSignal) -> list[Any]:
        field_name = signal.mapping_field or signal.field_name
        if not field_name:
            return []
        mapping_version_id = signal.mapping_version_id
        if not mapping_version_id:
            return []

        old_selector = await self._resolve_old_selector(mapping_version_id, field_name, signal)
        sample_pages = await self._load_sample_pages(signal)
        if not sample_pages:
            return []

        clusters = self._cluster_signal_context(signal, sample_pages)
        candidates = self._generate_candidate_selectors(
            old_selector=old_selector,
            field_name=field_name,
            sample_pages=sample_pages,
            signal=signal,
            clusters=clusters,
        )
        created: list[Any] = []
        for proposed_selector, heuristic_confidence, strategy_used, evidence in candidates[:5]:
            validation = self._validate_selector(proposed_selector, field_name, sample_pages)
            status = (
                "VALIDATED"
                if validation["success_rate"] >= 0.8
                and validation["valid_value_rate"] >= 0.8
                and validation["diversity_score"] >= 0.2
                and validation["consistency_score"] >= 0.4
                else "REJECTED"
            )
            confidence_score = await self._compute_dynamic_confidence(
                source_id=signal.source_id,
                field_name=field_name,
                heuristic_confidence=heuristic_confidence,
                validation=validation,
            )
            priority_score = self._compute_priority(
                severity=signal.severity,
                affected_pages=len(sample_pages),
                field_name=field_name,
            )
            reasoning = (
                f"{strategy_used} generated selector '{proposed_selector}' for field '{field_name}' "
                f"from clustered drift evidence and validated across {validation['sample_size']} pages."
            )
            proposal = MappingRepairProposal(
                source_id=signal.source_id,
                mapping_version_id=mapping_version_id,
                field_name=field_name,
                old_selector=old_selector,
                proposed_selector=proposed_selector,
                confidence_score=confidence_score,
                supporting_pages=[page.url for page in sample_pages[:10]],
                drift_signals_used=[signal.id],
                validation_results=validation,
                occurrence_count=1,
                priority_score=priority_score,
                strategy_used=strategy_used,
                reasoning=reasoning,
                evidence=evidence,
                status=status,
            )
            stored = await crud.upsert_mapping_repair_proposal(
                self.db,
                source_id=proposal.source_id,
                mapping_version_id=proposal.mapping_version_id,
                field_name=proposal.field_name,
                old_selector=proposal.old_selector,
                proposed_selector=proposal.proposed_selector,
                confidence_score=proposal.confidence_score,
                supporting_pages=proposal.supporting_pages,
                drift_signals_used=proposal.drift_signals_used,
                validation_results=proposal.validation_results,
                occurrence_count=proposal.occurrence_count,
                priority_score=proposal.priority_score,
                strategy_used=proposal.strategy_used,
                reasoning=proposal.reasoning,
                evidence=proposal.evidence or {},
                status=proposal.status,
            )
            created.append(stored)

        return created

    async def apply_proposal(self, source_id: str, proposal_id: str, *, reviewed_by: str) -> str:
        proposal = await crud.get_mapping_repair_proposal(self.db, source_id=source_id, proposal_id=proposal_id)
        if proposal is None:
            raise ValueError("Mapping repair proposal not found")
        if proposal.status not in {"VALIDATED", "DRAFT"}:
            raise ValueError("Only DRAFT or VALIDATED proposals can be applied")

        if proposal.mapping_version_id is None:
            raise RuntimeError("Proposal has no mapping version context for safe apply")
        baseline_pages = await self._load_pages_for_proposal(source_id, proposal)
        before_metrics = self._validate_selector(
            proposal.old_selector or proposal.proposed_selector,
            proposal.field_name,
            baseline_pages,
        )
        prior_validation = json.loads(proposal.validation_results_json or "{}") if proposal.validation_results_json else {}
        prior_success_rate = float(prior_validation.get("success_rate", 0.0))
        if prior_success_rate > before_metrics["success_rate"]:
            before_metrics["success_rate"] = round(prior_success_rate, 4)

        draft = await crud.clone_published_mapping_to_draft(self.db, source_id, created_by=reviewed_by)
        rows = await crud.list_source_mapping_rows(self.db, source_id, draft.id, skip=0, limit=5000)
        updated = 0
        for row in rows:
            if row.destination_field != proposal.field_name:
                continue
            if proposal.old_selector and row.selector != proposal.old_selector:
                continue
            row.selector = proposal.proposed_selector
            row.status = "approved"
            row.updated_at = datetime.now(UTC)
            updated += 1

        if updated == 0:
            raise RuntimeError("No mapping rows matched proposal for safe application")

        summary = json.loads(draft.summary_json or "{}") if draft.summary_json else {}
        summary["auto_repair_derived"] = True
        summary["auto_repair_proposal_id"] = proposal.id
        summary["auto_repair_updated_fields"] = [proposal.field_name]
        draft.summary_json = json.dumps(summary)
        await self.db.commit()

        published = await crud.publish_source_mapping_version(self.db, source_id, draft.id, published_by=reviewed_by)
        after_metrics = self._validate_selector(proposal.proposed_selector, proposal.field_name, baseline_pages)
        post_apply_success = after_metrics["success_rate"]
        if post_apply_success + 0.05 < before_metrics["success_rate"]:
            try:
                await crud.rollback_source_mapping_version(
                    self.db,
                    source_id,
                    proposal.mapping_version_id,
                    rolled_back_by=f"{reviewed_by}:auto-repair-guard",
                )
            except RuntimeError:
                await crud.update_source(
                    self.db,
                    source_id,
                    active_mapping_version_id=proposal.mapping_version_id,
                    mapping_status="published",
                )
            await crud.update_mapping_repair_proposal(
                self.db,
                source_id=source_id,
                proposal_id=proposal_id,
                status="REJECTED",
                feedback={
                    "decision": "auto_rollback",
                    "reason": "post_apply_drift_worsened",
                    "before_success_rate": before_metrics["success_rate"],
                    "after_success_rate": post_apply_success,
                    "rolled_back_to_mapping_version_id": proposal.mapping_version_id,
                    "rollback_at": datetime.now(UTC).isoformat(),
                },
            )
            logger.warning(
                "mapping_auto_repair_rolled_back",
                source_id=source_id,
                proposal_id=proposal_id,
                before_success_rate=before_metrics["success_rate"],
                after_success_rate=post_apply_success,
                rolled_back_to=proposal.mapping_version_id,
            )
            raise RuntimeError("Applied mapping degraded extraction quality and was rolled back automatically")

        await self._record_feedback_event(
            source_id=source_id,
            proposal=proposal,
            event_name="post_apply_success",
            extra={"before": before_metrics["success_rate"], "after": post_apply_success},
        )
        return published.id

    async def _resolve_old_selector(self, mapping_version_id: str, field_name: str, signal: MappingDriftSignal) -> str | None:
        if signal.failing_selector:
            return signal.failing_selector
        stmt = select(SourceMappingRow).where(
            SourceMappingRow.mapping_version_id == mapping_version_id,
            SourceMappingRow.destination_field == field_name,
            SourceMappingRow.is_enabled.is_(True),
        ).order_by(SourceMappingRow.updated_at.desc())
        row = (await self.db.execute(stmt.limit(1))).scalar_one_or_none()
        return row.selector if row else None

    async def _load_sample_pages(self, signal: MappingDriftSignal) -> list[Page]:
        sample_urls = json.loads(signal.sample_urls_json or "[]") if signal.sample_urls_json else []
        pages: list[Page] = []
        if signal.page_id:
            page_stmt = select(Page).where(Page.id == signal.page_id)
            page = (await self.db.execute(page_stmt)).scalar_one_or_none()
            if page and page.html:
                pages.append(page)
        if sample_urls:
            stmt = select(Page).where(Page.source_id == signal.source_id, Page.url.in_(sample_urls)).limit(20)
            matches = list((await self.db.execute(stmt)).scalars().all())
            pages.extend([p for p in matches if p.html])
        if not pages:
            stmt = (
                select(Page)
                .where(Page.source_id == signal.source_id, Page.mapping_version_id_used == signal.mapping_version_id)
                .order_by(Page.created_at.desc())
                .limit(10)
            )
            pages.extend([p for p in (await self.db.execute(stmt)).scalars().all() if p.html])
        seen: set[str] = set()
        unique_pages: list[Page] = []
        for page in pages:
            if page.id in seen:
                continue
            seen.add(page.id)
            unique_pages.append(page)
        return unique_pages[:10]

    def _generate_candidate_selectors(
        self,
        *,
        old_selector: str | None,
        field_name: str,
        sample_pages: list[Page],
        signal: MappingDriftSignal,
        clusters: dict[str, dict[str, str]],
    ) -> list[tuple[str, float, str, dict[str, Any]]]:
        candidates: list[tuple[str, float, str, dict[str, Any]]] = []
        if old_selector:
            for relaxed in self._relax_selector(old_selector):
                candidates.append((relaxed, 0.65, "relax_existing_selector", {"old_selector": old_selector}))

        selector_path = signal.selector_path
        if selector_path:
            candidates.append((selector_path, 0.6, "signal_selector_path", {"selector_path": selector_path}))

        diagnostics = json.loads(signal.diagnostics_json or "{}") if signal.diagnostics_json else {}
        expected_text = str(signal.previous_value or diagnostics.get("expected_text") or "").strip()

        tag_counter: dict[str, int] = {}
        class_counter: dict[str, int] = {}
        for page in sample_pages:
            soup = BeautifulSoup(page.html or "", "lxml")
            if expected_text:
                for node in soup.find_all(text=True):
                    value = str(node).strip()
                    if not value:
                        continue
                    sim = SequenceMatcher(None, expected_text.lower(), value.lower()).ratio()
                    if sim < 0.6:
                        continue
                    parent = node.parent
                    if not parent:
                        continue
                    if parent.name:
                        tag_counter[parent.name] = tag_counter.get(parent.name, 0) + 1
                    for cls in parent.get("class") or []:
                        class_counter[cls] = class_counter.get(cls, 0) + 1

        for tag, count in sorted(tag_counter.items(), key=lambda item: item[1], reverse=True)[:3]:
            candidates.append(
                (
                    tag,
                    min(0.75, 0.5 + (count / max(len(sample_pages), 1)) * 0.2),
                    "tag_frequency",
                    {"tag_hits": count},
                )
            )
        for cls, count in sorted(class_counter.items(), key=lambda item: item[1], reverse=True)[:3]:
            candidates.append(
                (
                    f".{cls}",
                    min(0.8, 0.55 + (count / max(len(sample_pages), 1)) * 0.25),
                    "class_frequency",
                    {"class_hits": count},
                )
            )

        for cluster in clusters.values():
            selector = cluster.get("selector")
            if selector:
                candidates.append((selector, 0.72, "clustered_signal", {"cluster": cluster}))

        fallback = f"[data-field*='{field_name}'], .{field_name}, [class*='{field_name}']"
        candidates.append((fallback, 0.45, "field_name_fallback", {"field_name": field_name}))

        dedup: dict[str, tuple[float, str, dict[str, Any]]] = {}
        for selector, conf, strategy_used, evidence in candidates:
            norm = selector.strip()
            if not norm:
                continue
            current = dedup.get(norm)
            if current is None or conf > current[0]:
                dedup[norm] = (conf, strategy_used, evidence)
        return sorted(
            [(selector, payload[0], payload[1], payload[2]) for selector, payload in dedup.items()],
            key=lambda item: item[1],
            reverse=True,
        )

    def _relax_selector(self, selector: str) -> list[str]:
        options: list[str] = []
        pieces = [part.strip() for part in selector.split(">") if part.strip()]
        if len(pieces) > 1:
            options.append(" > ".join(pieces[1:]))
            options.append(pieces[-1])

        if "." in selector and not selector.strip().startswith("."):
            before, _, after = selector.partition(".")
            if before:
                options.append(before)
            if after:
                options.append(f".{after.split('.')[0]}")
        elif selector.count(".") > 1 and selector.strip().startswith("."):
            options.append("." + selector.strip(".").split(".")[0])
        return options

    def _validate_selector(self, selector: str, field_name: str, pages: list[Page]) -> dict[str, Any]:
        success = 0
        valid = 0
        non_empty_values: list[str] = []
        samples: list[dict[str, str | None]] = []
        for page in pages:
            soup = BeautifulSoup(page.html or "", "lxml")
            node = soup.select_one(selector)
            value = node.get_text(" ", strip=True) if node else None
            ok = bool(value)
            if ok:
                success += 1
                non_empty_values.append(value.strip())
            plausible = self._is_plausible(field_name, value)
            if plausible:
                valid += 1
            samples.append({"url": page.url, "value": value})
        total = max(len(pages), 1)
        diversity = self._value_diversity(non_empty_values)
        consistency = self._cross_page_consistency(non_empty_values)
        pattern_valid_rate = self._pattern_validation_rate(field_name, non_empty_values)
        nonsensical_ratio = self._nonsensical_ratio(field_name, non_empty_values)
        return {
            "sample_size": len(pages),
            "success_rate": round(success / total, 4),
            "valid_value_rate": round(valid / total, 4),
            "diversity_score": diversity,
            "consistency_score": consistency,
            "pattern_valid_rate": pattern_valid_rate,
            "nonsensical_ratio": nonsensical_ratio,
            "sample_values": samples[:5],
        }

    def _is_plausible(self, field_name: str, value: str | None) -> bool:
        if value is None:
            return False
        text = value.strip()
        if not text:
            return False
        key = field_name.lower()
        if key.endswith("_url"):
            return text.startswith("http://") or text.startswith("https://") or text.startswith("/")
        if "date" in key:
            return any(ch.isdigit() for ch in text)
        if key in {"year", "birth_year"}:
            return text.isdigit() and 1000 <= int(text) <= 2100
        if key in {"title", "name"}:
            if text.lower() in {"n/a", "unknown", "none", "click here", "read more"}:
                return False
            if len(text) < 2:
                return False
        return True

    def _value_diversity(self, values: list[str]) -> float:
        if not values:
            return 0.0
        distinct = {v.strip().lower() for v in values if v.strip()}
        return round(len(distinct) / max(len(values), 1), 4)

    def _cross_page_consistency(self, values: list[str]) -> float:
        if not values:
            return 0.0
        counter = Counter(v.strip().lower() for v in values if v.strip())
        dominant = max(counter.values()) if counter else 0
        return round(1.0 - (dominant / max(len(values), 1)), 4)

    def _pattern_validation_rate(self, field_name: str, values: list[str]) -> float:
        if not values:
            return 0.0
        key = field_name.lower()
        passed = 0
        for value in values:
            text = value.strip()
            if key.endswith("_url"):
                ok = text.startswith(("http://", "https://", "/"))
            elif "date" in key:
                ok = bool(re.search(r"\d{4}", text))
            elif key in {"year", "birth_year"}:
                ok = text.isdigit() and 1000 <= int(text) <= 2100
            else:
                ok = len(text) > 1
            if ok:
                passed += 1
        return round(passed / max(len(values), 1), 4)

    def _nonsensical_ratio(self, field_name: str, values: list[str]) -> float:
        if not values:
            return 1.0
        invalid_tokens = {"n/a", "unknown", "none", "null", "-", "--", "click here", "read more"}
        key = field_name.lower()
        nonsensical = 0
        for value in values:
            text = value.strip().lower()
            if text in invalid_tokens:
                nonsensical += 1
                continue
            if key in {"year", "birth_year"} and not text.isdigit():
                nonsensical += 1
                continue
            if len(text) <= 1:
                nonsensical += 1
        return round(nonsensical / max(len(values), 1), 4)

    def _cluster_signal_context(self, signal: MappingDriftSignal, pages: list[Page]) -> dict[str, dict[str, str]]:
        clusters: dict[str, dict[str, str]] = {}
        selector = signal.failing_selector or signal.selector_path or "__no_selector__"
        node = signal.mapping_field or signal.field_name or "__unknown_field__"
        cluster_key = f"{node}|{selector}|{signal.mapping_version_id or 'none'}"
        sample_page = pages[0].url if pages else ""
        clusters[cluster_key] = {"field": node, "selector": selector if selector != "__no_selector__" else "", "sample_url": sample_page}
        return clusters

    def _compute_priority(self, *, severity: str, affected_pages: int, field_name: str) -> float:
        severity_weight = {"high": 1.0, "medium": 0.7, "low": 0.4}.get(severity.lower(), 0.5)
        field_weight = 1.0 if field_name.lower() in {"title", "name", "start_date", "venue_name"} else 0.7
        return round(severity_weight * max(affected_pages, 1) * field_weight, 4)

    async def _compute_dynamic_confidence(
        self,
        *,
        source_id: str,
        field_name: str,
        heuristic_confidence: float,
        validation: dict[str, Any],
    ) -> float:
        stats = await crud.get_mapping_repair_feedback_stats(self.db, source_id=source_id, field_name=field_name)
        accepted_rate = stats["accepted_rate"]
        apply_success_rate = stats["apply_success_rate"]
        confidence = (
            (heuristic_confidence * 0.45)
            + (validation["success_rate"] * 0.25)
            + (validation["valid_value_rate"] * 0.15)
            + (accepted_rate * 0.1)
            + (apply_success_rate * 0.05)
        )
        penalty = validation["nonsensical_ratio"] * 0.2
        return round(max(0.0, min(1.0, confidence - penalty)), 4)

    async def _load_pages_for_proposal(self, source_id: str, proposal: Any) -> list[Page]:
        urls = json.loads(proposal.supporting_pages_json or "[]")
        if not urls:
            return []
        stmt = select(Page).where(Page.source_id == source_id, Page.url.in_(urls)).limit(25)
        return [p for p in (await self.db.execute(stmt)).scalars().all() if p.html]

    async def _record_feedback_event(self, *, source_id: str, proposal: Any, event_name: str, extra: dict[str, Any]) -> None:
        previous_feedback = json.loads(proposal.feedback_json or "{}") if getattr(proposal, "feedback_json", None) else {}
        previous_feedback[event_name] = {"at": datetime.now(UTC).isoformat(), **extra}
        await crud.update_mapping_repair_proposal(
            self.db,
            source_id=source_id,
            proposal_id=proposal.id,
            feedback=previous_feedback,
        )
