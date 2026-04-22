from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Entity, EntityLink, Record


@dataclass
class EntityResolutionResult:
    entity: Entity
    link: EntityLink
    decision: str
    review_required: bool


class EntityResolver:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def resolve_record(self, record: Record) -> EntityResolutionResult:
        existing_link = await self._get_record_link(record.id)
        if existing_link is not None:
            entity = await self.db.get(Entity, existing_link.entity_id)
            if entity is None:
                raise ValueError(f"Entity {existing_link.entity_id} not found")
            return EntityResolutionResult(entity=entity, link=existing_link, decision="already_linked", review_required=False)

        best_entity, score, signals = await self._find_best_match(record)
        strong_match = score >= 0.88 and signals.get("name_similarity", 0.0) >= 0.82
        medium_match = score >= 0.72 and signals.get("name_similarity", 0.0) >= 0.65

        if best_entity is not None and strong_match:
            link = await self._create_link(best_entity, record, score, "exact" if signals.get("name_similarity", 0.0) >= 0.99 else "fuzzy")
            await self._merge_entity(best_entity, record, score)
            return EntityResolutionResult(entity=best_entity, link=link, decision="link_to_entity", review_required=False)

        entity = await self._create_entity_from_record(record)
        method = "manual" if medium_match else "exact"
        link = await self._create_link(entity, record, score if medium_match else max(record.confidence_score / 100.0, 0.5), method)
        await self._merge_entity(entity, record, score if medium_match else max(record.confidence_score / 100.0, 0.5))

        if medium_match:
            data = dict(entity.canonical_data or {})
            conflicts = list(data.get("conflicts", []))
            conflicts.append(
                {
                    "field": "entity_resolution",
                    "reason": "medium_match_requires_review",
                    "candidate_entity_id": best_entity.id if best_entity else None,
                    "score": score,
                    "signals": signals,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
            data["conflicts"] = conflicts
            entity.canonical_data = data
            await self.db.commit()
            await self.db.refresh(entity)
            return EntityResolutionResult(entity=entity, link=link, decision="create_entity_flag_review", review_required=True)

        return EntityResolutionResult(entity=entity, link=link, decision="create_new_entity", review_required=False)

    async def _find_best_match(self, record: Record) -> tuple[Entity | None, float, dict[str, float]]:
        name = (record.title or "").strip()
        if not name:
            return None, 0.0, {}
        result = await self.db.execute(select(Entity).where(Entity.entity_type == record.record_type).limit(500))
        candidates = list(result.scalars().all())
        best: tuple[Entity, float, dict[str, float]] | None = None
        for entity in candidates:
            signals = self._score_signals(record, entity)
            total = signals.get("name_similarity", 0.0) * 0.7 + signals.get("secondary", 0.0) * 0.3
            if best is None or total > best[1]:
                best = (entity, total, signals)
        if best is None:
            return None, 0.0, {}
        return best

    def _score_signals(self, record: Record, entity: Entity) -> dict[str, float]:
        name_similarity = SequenceMatcher(None, (record.title or "").lower().strip(), (entity.canonical_name or "").lower().strip()).ratio()
        canonical = entity.canonical_data or {}
        canonical_fields = canonical.get("fields", canonical) if isinstance(canonical, dict) else {}
        secondary = 0.0

        def _eq(a: Any, b: Any) -> bool:
            return bool(a) and bool(b) and str(a).strip().lower() == str(b).strip().lower()

        if record.record_type == "artist":
            points = [_eq(record.birth_year, canonical_fields.get("birth_year")), _eq(record.nationality, canonical_fields.get("nationality"))]
            secondary = sum(1.0 for p in points if p) / 2
        elif record.record_type == "artwork":
            points = [_eq(record.medium, canonical_fields.get("medium")), _eq(record.year, canonical_fields.get("year"))]
            secondary = sum(1.0 for p in points if p) / 2
        elif record.record_type == "exhibition":
            points = [_eq(record.venue_name, canonical_fields.get("venue_name")), _eq(record.start_date, canonical_fields.get("start_date"))]
            secondary = sum(1.0 for p in points if p) / 2
        elif record.record_type == "event":
            points = [_eq(record.venue_name, canonical_fields.get("venue_name")), _eq(record.start_date, canonical_fields.get("start_date"))]
            secondary = sum(1.0 for p in points if p) / 2
        elif record.record_type == "venue":
            secondary = 1.0 if _eq(record.address, canonical_fields.get("address")) else 0.0

        return {"name_similarity": name_similarity, "secondary": secondary}

    async def _create_entity_from_record(self, record: Record) -> Entity:
        payload = self._record_payload(record)
        entity = Entity(
            source_id=record.source_id,
            entity_type=record.record_type,
            canonical_name=record.title or payload.get("title") or "Untitled",
            canonical_data={"fields": payload, "provenance": {}, "conflicts": []},
            confidence_score=max(record.confidence_score / 100.0, 0.5),
        )
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def _create_link(self, entity: Entity, record: Record, confidence: float, method: str) -> EntityLink:
        existing = await self._get_record_link(record.id)
        if existing is not None:
            return existing
        link = EntityLink(
            entity_id=entity.id,
            record_id=record.id,
            source_id=record.source_id,
            confidence_score=max(0.0, min(confidence, 1.0)),
            match_method=method,
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def _merge_entity(self, entity: Entity, record: Record, link_confidence: float) -> None:
        payload = self._record_payload(record)
        data = dict(entity.canonical_data or {})
        fields = dict(data.get("fields", {}))
        provenance = dict(data.get("provenance", {}))
        conflicts = list(data.get("conflicts", []))
        incoming_confidence = max(0.0, min(record.confidence_score / 100.0, 1.0))

        for key, value in payload.items():
            if value in (None, "", []):
                continue
            current_value = fields.get(key)
            entries = list(provenance.get(key, []))
            best_existing = max((float(e.get("confidence", 0.0)) for e in entries), default=0.0)
            entries.append(
                {
                    "record_id": record.id,
                    "source_id": record.source_id,
                    "confidence": incoming_confidence,
                    "value": value,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
            provenance[key] = entries
            if current_value in (None, ""):
                fields[key] = value
                continue
            if current_value != value:
                if incoming_confidence >= best_existing:
                    conflicts.append({
                        "field": key,
                        "existing_value": current_value,
                        "incoming_value": value,
                        "resolution": "replaced",
                        "record_id": record.id,
                        "created_at": datetime.now(UTC).isoformat(),
                    })
                    fields[key] = value
                else:
                    conflicts.append({
                        "field": key,
                        "existing_value": current_value,
                        "incoming_value": value,
                        "resolution": "kept_existing",
                        "record_id": record.id,
                        "created_at": datetime.now(UTC).isoformat(),
                    })

        entity.canonical_data = {
            "fields": fields,
            "provenance": provenance,
            "conflicts": conflicts,
        }
        entity.canonical_name = fields.get("title") or entity.canonical_name
        entity.confidence_score = max(float(entity.confidence_score or 0.0), incoming_confidence)
        entity.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(entity)

    async def _get_record_link(self, record_id: str) -> EntityLink | None:
        result = await self.db.execute(select(EntityLink).where(EntityLink.record_id == record_id))
        return result.scalar_one_or_none()

    def _record_payload(self, record: Record) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": record.title,
            "description": record.description,
            "start_date": record.start_date,
            "end_date": record.end_date,
            "venue_name": record.venue_name,
            "venue_address": record.venue_address,
            "bio": record.bio,
            "nationality": record.nationality,
            "birth_year": record.birth_year,
            "address": record.address,
            "city": record.city,
            "country": record.country,
            "medium": record.medium,
            "year": record.year,
            "source_url": record.source_url,
        }
        return {k: v for k, v in payload.items() if v not in (None, "")}
