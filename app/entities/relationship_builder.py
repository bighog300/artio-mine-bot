from __future__ import annotations

import json
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Entity, EntityLink, EntityRelationship, Record
from app.entities.reconciliation import EntityGraphReconciler


class EntityRelationshipBuilder:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build_for_record(self, record: Record) -> int:
        source_entity = await self._entity_for_record(record.id)
        if source_entity is None:
            return 0
        created = 0

        if record.record_type == "artwork":
            for artist_name in self._artist_names(record):
                target = await self._find_entity_by_name("artist", artist_name)
                if target and await self._upsert(source_entity.id, target.id, "CREATED_BY", record):
                    created += 1

        if record.record_type == "exhibition":
            if record.venue_name:
                target = await self._find_entity_by_name("venue", record.venue_name)
                if target and await self._upsert(source_entity.id, target.id, "EXHIBITED_AT", record):
                    created += 1

        if record.record_type == "artist" and record.title:
            exhibitions = await self._related_exhibitions(record)
            for exhibition in exhibitions:
                target = await self._entity_for_record(exhibition.id)
                if target and await self._upsert(source_entity.id, target.id, "PARTICIPATED_IN", exhibition):
                    created += 1

        if record.record_type == "event":
            if record.venue_name:
                target = await self._find_entity_by_name("venue", record.venue_name)
                if target and await self._upsert(target.id, source_entity.id, "HOSTED_EVENT", record):
                    created += 1

        if record.record_type == "venue" and record.title:
            events = await self._related_events(record)
            for event in events:
                target = await self._entity_for_record(event.id)
                if target and await self._upsert(source_entity.id, target.id, "HOSTED_EVENT", event):
                    created += 1

        return created

    async def _entity_for_record(self, record_id: str) -> Entity | None:
        link_result = await self.db.execute(select(EntityLink).where(EntityLink.record_id == record_id))
        link = link_result.scalar_one_or_none()
        if link is None:
            return None
        return await self.db.get(Entity, link.entity_id)

    async def _find_entity_by_name(self, entity_type: str, name: str) -> Entity | None:
        value = name.strip().lower()
        if not value:
            return None
        result = await self.db.execute(select(Entity).where(Entity.entity_type == entity_type, Entity.is_deleted.is_(False)).limit(500))
        best: tuple[Entity, float] | None = None
        for entity in result.scalars().all():
            score = SequenceMatcher(None, (entity.canonical_name or "").strip().lower(), value).ratio()
            if best is None or score > best[1]:
                best = (entity, score)
        if best is None or best[1] < 0.9:
            return None
        return best[0]

    async def _upsert(self, from_entity_id: str, to_entity_id: str, relationship_type: str, source_record: Record) -> bool:
        result = await self.db.execute(
            select(EntityRelationship).where(
                EntityRelationship.from_entity_id == from_entity_id,
                EntityRelationship.to_entity_id == to_entity_id,
                EntityRelationship.relationship_type == relationship_type,
            )
        )
        existing = result.scalar_one_or_none()
        incoming_confidence = max(source_record.confidence_score / 100.0, 0.5)
        metadata = json.dumps(
            {
                "signals": [
                    {
                        "source_record_id": source_record.id,
                        "source_page_id": source_record.page_id,
                        "confidence": incoming_confidence,
                    }
                ],
                "reinforcement_count": 1,
            }
        )

        if existing is not None:
            reconciler = EntityGraphReconciler(self.db)
            existing.confidence_score = await reconciler.aggregate_relationship_confidence(existing, incoming_confidence)
            existing.metadata_json = reconciler._merge_relationship_metadata(existing.metadata_json, metadata)
            await self.db.commit()
            return False

        rel = EntityRelationship(
            source_id=source_record.source_id,
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            relationship_type=relationship_type,
            confidence_score=incoming_confidence,
            source_record_id=source_record.id,
            metadata_json=metadata,
        )
        self.db.add(rel)
        await self.db.commit()
        return True

    async def _related_exhibitions(self, artist_record: Record) -> list[Record]:
        result = await self.db.execute(select(Record).where(Record.record_type == "exhibition").limit(5000))
        name = (artist_record.title or "").strip().lower()
        matches: list[Record] = []
        for record in result.scalars().all():
            artist_names: list[str] = []
            try:
                parsed = json.loads(record.artist_names or "[]")
                if isinstance(parsed, list):
                    artist_names = [str(item).strip().lower() for item in parsed]
            except json.JSONDecodeError:
                artist_names = []
            if name and name in artist_names:
                matches.append(record)
        return matches

    async def _related_events(self, venue_record: Record) -> list[Record]:
        result = await self.db.execute(select(Record).where(Record.record_type == "event").limit(5000))
        target = (venue_record.title or "").strip().lower()
        return [
            event
            for event in result.scalars().all()
            if (event.venue_name or "").strip().lower() == target
        ]

    def _artist_names(self, record: Record) -> list[str]:
        names: list[str] = []
        if record.artist_names:
            try:
                parsed = json.loads(record.artist_names)
                if isinstance(parsed, list):
                    names = [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                names = []
        return names
