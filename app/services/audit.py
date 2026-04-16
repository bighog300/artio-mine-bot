from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import AuditEvent


class AuditService:
    @staticmethod
    def _parse_dt(value: str | None, *, end_of_day: bool = False) -> datetime | None:
        if not value:
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        if end_of_day and len(value) == 10:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed

    @staticmethod
    def _deserialize_event(event: AuditEvent) -> dict[str, Any]:
        try:
            changes = json.loads(event.changes_json) if event.changes_json else None
        except json.JSONDecodeError:
            changes = None
        try:
            metadata = json.loads(event.metadata_json) if event.metadata_json else {}
        except json.JSONDecodeError:
            metadata = {}

        return {
            "id": event.id,
            "timestamp": event.created_at,
            "event_type": event.event_type,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "user_id": event.user_id,
            "user_name": event.user_name,
            "source_id": event.source_id,
            "record_id": event.record_id,
            "message": event.message,
            "changes": changes,
            "metadata": metadata,
        }

    @classmethod
    async def list_events(
        cls,
        db: AsyncSession,
        *,
        event_type: str | None = None,
        entity_type: str | None = None,
        user_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        start_dt = cls._parse_dt(date_from)
        end_dt = cls._parse_dt(date_to, end_of_day=True)
        events = await crud.list_audit_events(
            db,
            event_type=event_type,
            entity_type=entity_type,
            user_id=user_id,
            date_from=start_dt,
            date_to=end_dt,
            search=search,
            skip=skip,
            limit=limit,
        )
        total = await crud.count_audit_events(
            db,
            event_type=event_type,
            entity_type=entity_type,
            user_id=user_id,
            date_from=start_dt,
            date_to=end_dt,
            search=search,
        )
        return {
            "items": [cls._deserialize_event(event) for event in events],
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    @classmethod
    async def get_event(cls, db: AsyncSession, event_id: str) -> dict[str, Any] | None:
        event = await crud.get_audit_event(db, event_id)
        if event is None:
            return None
        return cls._deserialize_event(event)

    @classmethod
    async def export_events_csv(
        cls,
        db: AsyncSession,
        *,
        event_type: str | None = None,
        entity_type: str | None = None,
        user_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
    ) -> str:
        response = await cls.list_events(
            db,
            event_type=event_type,
            entity_type=entity_type,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
            skip=0,
            limit=5000,
        )

        out = io.StringIO()
        writer = csv.DictWriter(
            out,
            fieldnames=[
                "id",
                "timestamp",
                "event_type",
                "entity_type",
                "entity_id",
                "user_id",
                "user_name",
                "source_id",
                "record_id",
                "message",
                "changes",
                "metadata",
            ],
        )
        writer.writeheader()
        for item in response["items"]:
            writer.writerow(
                {
                    **item,
                    "timestamp": item["timestamp"].isoformat() if item.get("timestamp") else "",
                    "changes": json.dumps(item.get("changes") or {}),
                    "metadata": json.dumps(item.get("metadata") or {}),
                }
            )
        return out.getvalue()
