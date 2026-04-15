from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_conflict_value(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return [normalize_conflict_value(v) for v in value]
    if isinstance(value, dict):
        return {k: normalize_conflict_value(v) for k, v in value.items()}
    return value


def values_conflict(existing: Any, candidate: Any) -> bool:
    if existing in (None, "", []):
        return False
    if candidate in (None, "", []):
        return False
    return normalize_conflict_value(existing) != normalize_conflict_value(candidate)
