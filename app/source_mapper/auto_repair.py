from __future__ import annotations

import json
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

        candidates = self._generate_candidate_selectors(
            old_selector=old_selector,
            field_name=field_name,
            sample_pages=sample_pages,
            signal=signal,
        )
        created: list[Any] = []
        for proposed_selector, heuristic_confidence in candidates[:5]:
            validation = self._validate_selector(proposed_selector, field_name, sample_pages)
            status = "VALIDATED" if validation["success_rate"] >= 0.8 and validation["valid_value_rate"] >= 0.8 else "REJECTED"
            confidence_score = round((heuristic_confidence * 0.6) + (validation["success_rate"] * 0.4), 4)
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
                status=status,
            )
            stored = await crud.create_mapping_repair_proposal(
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
                status=proposal.status,
            )
            created.append(stored)

            should_auto_apply = (
                proposal.status == "VALIDATED"
                and proposal.confidence_score >= 0.9
                and validation["success_rate"] >= 0.9
                and validation["sample_size"] >= 3
            )
            if should_auto_apply:
                try:
                    new_mapping_id = await self.apply_proposal(signal.source_id, stored.id, reviewed_by="system:auto")
                    await crud.update_mapping_repair_proposal(
                        self.db,
                        source_id=signal.source_id,
                        proposal_id=stored.id,
                        status="APPLIED",
                        feedback={"auto_applied": True, "applied_at": datetime.now(UTC).isoformat()},
                        applied_mapping_version_id=new_mapping_id,
                    )
                except (ValueError, RuntimeError, TypeError) as exc:
                    logger.warning("mapping_auto_apply_failed", source_id=signal.source_id, proposal_id=stored.id, error=str(exc))

        return created

    async def apply_proposal(self, source_id: str, proposal_id: str, *, reviewed_by: str) -> str:
        proposal = await crud.get_mapping_repair_proposal(self.db, source_id=source_id, proposal_id=proposal_id)
        if proposal is None:
            raise ValueError("Mapping repair proposal not found")
        if proposal.status not in {"VALIDATED", "DRAFT"}:
            raise ValueError("Only DRAFT or VALIDATED proposals can be applied")

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
    ) -> list[tuple[str, float]]:
        candidates: list[tuple[str, float]] = []
        if old_selector:
            for relaxed in self._relax_selector(old_selector):
                candidates.append((relaxed, 0.65))

        selector_path = signal.selector_path
        if selector_path:
            candidates.append((selector_path, 0.6))

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
            candidates.append((tag, min(0.75, 0.5 + (count / max(len(sample_pages), 1)) * 0.2)))
        for cls, count in sorted(class_counter.items(), key=lambda item: item[1], reverse=True)[:3]:
            candidates.append((f".{cls}", min(0.8, 0.55 + (count / max(len(sample_pages), 1)) * 0.25)))

        fallback = f"[data-field*='{field_name}'], .{field_name}, [class*='{field_name}']"
        candidates.append((fallback, 0.45))

        dedup: dict[str, float] = {}
        for selector, conf in candidates:
            norm = selector.strip()
            if not norm:
                continue
            dedup[norm] = max(conf, dedup.get(norm, 0.0))
        return sorted(dedup.items(), key=lambda item: item[1], reverse=True)

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
        samples: list[dict[str, str | None]] = []
        for page in pages:
            soup = BeautifulSoup(page.html or "", "lxml")
            node = soup.select_one(selector)
            value = node.get_text(" ", strip=True) if node else None
            ok = bool(value)
            if ok:
                success += 1
            plausible = self._is_plausible(field_name, value)
            if plausible:
                valid += 1
            samples.append({"url": page.url, "value": value})
        total = max(len(pages), 1)
        return {
            "sample_size": len(pages),
            "success_rate": round(success / total, 4),
            "valid_value_rate": round(valid / total, 4),
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
        return True
