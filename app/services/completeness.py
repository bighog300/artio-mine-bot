"""Data completeness calculation service for records."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Record


RECORD_TYPE_FIELDS: dict[str, dict[str, list[str]]] = {
    "artist": {
        "critical": ["title", "source_url"],
        "important": ["bio", "nationality", "birth_year", "website_url"],
        "optional": ["instagram_url", "email", "avatar_url", "mediums", "collections"],
    },
    "event": {
        "critical": ["title", "source_url", "start_date"],
        "important": ["venue_name", "end_date", "description"],
        "optional": ["ticket_url", "price_text", "curator", "is_free"],
    },
    "exhibition": {
        "critical": ["title", "source_url", "start_date"],
        "important": ["venue_name", "end_date", "description", "curator"],
        "optional": ["ticket_url", "price_text", "artist_names"],
    },
    "venue": {
        "critical": ["title", "source_url"],
        "important": ["address", "city", "country"],
        "optional": ["phone", "opening_hours", "website_url", "email"],
    },
    "artwork": {
        "critical": ["title", "source_url"],
        "important": ["medium", "year", "artist_names"],
        "optional": ["dimensions", "price", "description"],
    },
}


def _is_populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value not in {"", "[]", "{}"}
    if isinstance(value, (list, dict, set, tuple)):
        return len(value) > 0
    return True


def calculate_completeness(record: Record) -> dict[str, Any]:
    """Calculate completeness score and identify missing fields."""
    if record.record_type not in RECORD_TYPE_FIELDS:
        return {
            "score": 0,
            "total_fields": 0,
            "populated_fields": 0,
            "missing_fields": [],
            "critical_missing": [],
            "has_critical_missing": False,
        }

    fields = RECORD_TYPE_FIELDS[record.record_type]
    all_fields = fields["critical"] + fields["important"] + fields["optional"]

    populated: list[str] = []
    missing: list[str] = []
    critical_missing: list[str] = []

    for field in all_fields:
        value = getattr(record, field, None)
        if _is_populated(value):
            populated.append(field)
        else:
            missing.append(field)
            if field in fields["critical"]:
                critical_missing.append(field)

    score = int((len(populated) / len(all_fields)) * 100) if all_fields else 0
    return {
        "score": score,
        "total_fields": len(all_fields),
        "populated_fields": len(populated),
        "missing_fields": missing,
        "critical_missing": critical_missing,
        "has_critical_missing": len(critical_missing) > 0,
    }


async def update_record_completeness(db: AsyncSession, record: Record) -> dict[str, Any]:
    """Update completeness fields on a record."""
    completeness = calculate_completeness(record)
    record.completeness_score = completeness["score"]
    record.completeness_details = json.dumps(
        {
            "missing_fields": completeness["missing_fields"],
            "critical_missing": completeness["critical_missing"],
        }
    )
    await db.flush()
    return completeness


async def batch_update_completeness(db: AsyncSession, record_type: str | None = None) -> int:
    """Update completeness scores for all matching records."""
    stmt = select(Record)
    if record_type:
        stmt = stmt.where(Record.record_type == record_type)

    result = await db.execute(stmt)
    records = result.scalars().all()

    count = 0
    for record in records:
        await update_record_completeness(db, record)
        count += 1
        if count % 100 == 0:
            await db.commit()

    await db.commit()
    return count
