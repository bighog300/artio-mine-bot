from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from difflib import SequenceMatcher
from itertools import combinations
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Entity, EntityLink, EntityRelationship, Record


class EntityGraphReconciler:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_reconciliation_pass(self, *, min_match_score: float = 0.94, block_prefix_len: int = 3) -> dict[str, int]:
        entities = await self._active_entities()
        blocks: dict[tuple[str, str], list[Entity]] = defaultdict(list)
        for entity in entities:
            key = (entity.entity_type, self._blocking_key(entity.canonical_name, block_prefix_len))
            blocks[key].append(entity)

        scanned_pairs = 0
        merged_pairs = 0
        for block_entities in blocks.values():
            if len(block_entities) < 2:
                continue
            for left, right in combinations(block_entities, 2):
                if left.is_deleted or right.is_deleted:
                    continue
                scanned_pairs += 1
                score = self._entity_match_score(left, right)
                if score < min_match_score:
                    continue
                await self.merge_entities(left.id, right.id, min_match_score=min_match_score)
                merged_pairs += 1

        return {
            "blocks": len(blocks),
            "scanned_pairs": scanned_pairs,
            "merged_pairs": merged_pairs,
        }

    async def merge_entities(self, entity_a_id: str, entity_b_id: str, *, min_match_score: float = 0.94) -> Entity:
        entity_a = await self.db.get(Entity, entity_a_id)
        entity_b = await self.db.get(Entity, entity_b_id)
        if entity_a is None or entity_b is None:
            raise ValueError("entity not found")
        if entity_a.id == entity_b.id:
            return entity_a
        if entity_a.is_deleted or entity_b.is_deleted:
            raise ValueError("cannot merge deleted entities")
        if entity_a.entity_type != entity_b.entity_type:
            raise ValueError("unsafe merge rejected: different entity types")

        score = self._entity_match_score(entity_a, entity_b)
        if score < min_match_score:
            raise ValueError("unsafe merge rejected: weak similarity")

        winner, loser = self._winner(entity_a, entity_b)

        await self._merge_canonical_data(winner, loser)
        await self._reassign_entity_links(winner, loser)
        await self._merge_relationships(winner, loser)
        await self.recompute_canonical_data(winner.id)

        loser_data = dict(loser.canonical_data or {})
        merge_events = list(loser_data.get("merge_events", []))
        merge_events.append(
            {
                "merged_into_entity_id": winner.id,
                "merged_at": datetime.now(UTC).isoformat(),
                "match_score": score,
            }
        )
        loser_data["merge_events"] = merge_events
        loser.canonical_data = loser_data
        loser.is_deleted = True
        loser.deleted_at = datetime.now(UTC)
        loser.merged_into_entity_id = winner.id
        loser.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(winner)
        return winner

    async def recompute_canonical_data(self, entity_id: str) -> Entity:
        entity = await self.db.get(Entity, entity_id)
        if entity is None:
            raise ValueError("entity not found")

        records = await self._records_for_entity(entity.id)
        existing_data = dict(entity.canonical_data or {})
        field_signals: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for record in records:
            link = await self._link_for_record(entity.id, record.id)
            if link is None:
                continue
            weight = max(0.05, min(link.confidence_score, 1.0))
            for key, value in self._record_payload(record).items():
                if value in (None, "", []):
                    continue
                field_signals[key].append(
                    {
                        "value": value,
                        "record_id": record.id,
                        "source_id": record.source_id,
                        "confidence": weight,
                        "captured_at": datetime.now(UTC).isoformat(),
                    }
                )

        fields: dict[str, Any] = {}
        provenance: dict[str, list[dict[str, Any]]] = {}
        for field, entries in field_signals.items():
            if not entries:
                continue
            grouped: dict[str, float] = defaultdict(float)
            raw_values: dict[str, Any] = {}
            for entry in entries:
                key = str(entry["value"]).strip().lower()
                grouped[key] += float(entry["confidence"])
                raw_values[key] = entry["value"]
            winner_key = max(grouped.items(), key=lambda item: item[1])[0]
            fields[field] = raw_values[winner_key]
            provenance[field] = entries

        existing_conflicts = existing_data.get("conflicts", [])
        if not isinstance(existing_conflicts, list):
            existing_conflicts = []

        entity.canonical_data = {
            "fields": fields,
            "provenance": provenance,
            "conflicts": existing_conflicts,
            "recomputed_at": datetime.now(UTC).isoformat(),
        }
        entity.canonical_name = str(fields.get("title") or entity.canonical_name)
        entity.confidence_score = await self.compute_entity_confidence(entity.id)
        entity.updated_at = datetime.now(UTC)
        await self.db.flush()
        return entity

    async def compute_entity_confidence(self, entity_id: str) -> float:
        links_result = await self.db.execute(select(EntityLink).where(EntityLink.entity_id == entity_id))
        links = list(links_result.scalars().all())
        if not links:
            return 0.0

        record_count = len(links)
        average_confidence = sum(float(link.confidence_score or 0.0) for link in links) / record_count

        source_ids = {link.source_id for link in links if link.source_id}
        source_diversity = min(len(source_ids), 10) / 10.0
        record_signal = min(record_count, 20) / 20.0
        total = (record_signal * 0.35) + (average_confidence * 0.45) + (source_diversity * 0.20)
        return max(0.0, min(total, 1.0))

    async def aggregate_relationship_confidence(self, relationship: EntityRelationship, incoming: float) -> float:
        existing = max(0.0, min(float(relationship.confidence_score or 0.0), 1.0))
        signal = max(0.0, min(float(incoming), 1.0))
        reinforced = 1.0 - ((1.0 - existing) * (1.0 - (signal * 0.85)))
        return max(existing, min(reinforced, 1.0))

    async def _merge_canonical_data(self, winner: Entity, loser: Entity) -> None:
        winner_data = dict(winner.canonical_data or {})
        loser_data = dict(loser.canonical_data or {})

        winner_fields = dict(winner_data.get("fields", {}))
        loser_fields = dict(loser_data.get("fields", {}))
        winner_provenance = dict(winner_data.get("provenance", {}))
        loser_provenance = dict(loser_data.get("provenance", {}))
        conflicts = list(winner_data.get("conflicts", []))
        conflicts.extend(list(loser_data.get("conflicts", [])))

        for key, value in loser_fields.items():
            if key not in winner_fields and value not in (None, "", []):
                winner_fields[key] = value
        for key, entries in loser_provenance.items():
            merged = list(winner_provenance.get(key, []))
            merged.extend(entries if isinstance(entries, list) else [entries])
            winner_provenance[key] = merged

        winner.canonical_data = {
            "fields": winner_fields,
            "provenance": winner_provenance,
            "conflicts": conflicts,
            "merged_entity_ids": sorted({*(winner_data.get("merged_entity_ids", []) or []), loser.id}),
        }
        winner.updated_at = datetime.now(UTC)
        await self.db.flush()

    async def _reassign_entity_links(self, winner: Entity, loser: Entity) -> None:
        links = list((await self.db.execute(select(EntityLink).where(EntityLink.entity_id == loser.id))).scalars().all())
        for link in links:
            existing = (
                await self.db.execute(
                    select(EntityLink).where(
                        EntityLink.entity_id == winner.id,
                        EntityLink.record_id == link.record_id,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                existing.confidence_score = max(existing.confidence_score, link.confidence_score)
                await self.db.delete(link)
                continue
            link.entity_id = winner.id
        await self.db.flush()

    async def _merge_relationships(self, winner: Entity, loser: Entity) -> None:
        rels = list(
            (
                await self.db.execute(
                    select(EntityRelationship).where(
                        (EntityRelationship.from_entity_id == loser.id) | (EntityRelationship.to_entity_id == loser.id)
                    )
                )
            ).scalars().all()
        )
        for rel in rels:
            if rel.from_entity_id == loser.id:
                rel.from_entity_id = winner.id
            if rel.to_entity_id == loser.id:
                rel.to_entity_id = winner.id
            if rel.from_entity_id == rel.to_entity_id:
                await self.db.delete(rel)
                continue
            duplicate = (
                await self.db.execute(
                    select(EntityRelationship).where(
                        EntityRelationship.id != rel.id,
                        EntityRelationship.from_entity_id == rel.from_entity_id,
                        EntityRelationship.to_entity_id == rel.to_entity_id,
                        EntityRelationship.relationship_type == rel.relationship_type,
                    )
                )
            ).scalar_one_or_none()
            if duplicate is None:
                continue
            duplicate.confidence_score = await self.aggregate_relationship_confidence(duplicate, rel.confidence_score)
            duplicate.metadata_json = self._merge_relationship_metadata(duplicate.metadata_json, rel.metadata_json)
            await self.db.delete(rel)
        await self.db.flush()

    def _entity_match_score(self, left: Entity, right: Entity) -> float:
        name_score = SequenceMatcher(None, (left.canonical_name or "").lower().strip(), (right.canonical_name or "").lower().strip()).ratio()
        left_fields = (left.canonical_data or {}).get("fields", {}) if isinstance(left.canonical_data, dict) else {}
        right_fields = (right.canonical_data or {}).get("fields", {}) if isinstance(right.canonical_data, dict) else {}
        overlap = 0.0
        overlap_fields = ["birth_year", "nationality", "venue_name", "start_date", "address", "city", "country", "year", "medium"]
        matches = 0
        considered = 0
        for key in overlap_fields:
            lv = left_fields.get(key)
            rv = right_fields.get(key)
            if lv in (None, "") or rv in (None, ""):
                continue
            considered += 1
            if str(lv).strip().lower() == str(rv).strip().lower():
                matches += 1
        if considered:
            overlap = matches / considered
            return (name_score * 0.8) + (overlap * 0.2)
        return name_score

    def _winner(self, entity_a: Entity, entity_b: Entity) -> tuple[Entity, Entity]:
        if (entity_a.confidence_score or 0.0) >= (entity_b.confidence_score or 0.0):
            return entity_a, entity_b
        return entity_b, entity_a

    async def _active_entities(self) -> list[Entity]:
        result = await self.db.execute(select(Entity).where(Entity.is_deleted.is_(False)).order_by(Entity.entity_type, Entity.canonical_name))
        return list(result.scalars().all())

    async def _records_for_entity(self, entity_id: str) -> list[Record]:
        result = await self.db.execute(
            select(Record)
            .join(EntityLink, EntityLink.record_id == Record.id)
            .where(EntityLink.entity_id == entity_id)
        )
        return list(result.scalars().all())

    async def _link_for_record(self, entity_id: str, record_id: str) -> EntityLink | None:
        result = await self.db.execute(
            select(EntityLink).where(EntityLink.entity_id == entity_id, EntityLink.record_id == record_id)
        )
        return result.scalar_one_or_none()

    def _blocking_key(self, canonical_name: str, prefix_len: int) -> str:
        value = "".join(ch for ch in (canonical_name or "").lower().strip() if ch.isalnum())
        return value[:prefix_len] if value else ""

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

    def _merge_relationship_metadata(self, first: str | None, second: str | None) -> str:
        import json

        def _parse(payload: str | None) -> dict[str, Any]:
            if not payload:
                return {"signals": []}
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    parsed.setdefault("signals", [])
                    return parsed
            except json.JSONDecodeError:
                return {"signals": []}
            return {"signals": []}

        merged = _parse(first)
        incoming = _parse(second)
        signals = list(merged.get("signals", []))
        signals.extend(incoming.get("signals", []))
        merged["signals"] = signals
        merged["reinforcement_count"] = len(signals)
        return json.dumps(merged)
