from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from typing import Any

from app.records.schema import RecordType, StructuredRecordPayload

ARRAY_FIELDS = {"artist_names", "mediums", "collections"}
KEY_FINGERPRINT_FIELDS = (
    "title",
    "start_date",
    "end_date",
    "venue_name",
    "birth_year",
    "city",
    "country",
)


def normalize_record_type(value: str | RecordType) -> RecordType:
    if isinstance(value, RecordType):
        return value
    normalized = value.strip().lower()
    aliases = {
        "artist": RecordType.ARTIST,
        "artwork": RecordType.ARTWORK,
        "exhibition": RecordType.EXHIBITION,
        "event": RecordType.EVENT,
        "venue": RecordType.VENUE,
        "artist_article": RecordType.ARTWORK,
        "artist_press": RecordType.ARTWORK,
        "artist_memory": RecordType.ARTWORK,
        "article": RecordType.ARTWORK,
    }
    if normalized not in aliases:
        raise ValueError(f"Unsupported record_type '{value}'. Allowed: {[t.value for t in RecordType]}")
    return aliases[normalized]


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"\s+", " ", name.strip().lower())
    return re.sub(r"[^a-z0-9 ]", "", cleaned)


def build_fingerprint(normalized_name: str, values: dict[str, Any]) -> str:
    parts = [normalized_name]
    for field in KEY_FINGERPRINT_FIELDS:
        value = values.get(field)
        if value is None:
            continue
        if isinstance(value, list):
            value = sorted(str(v).strip().lower() for v in value if v)
        parts.append(f"{field}:{value}")
    payload = "|".join(str(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_field_confidence(values: dict[str, Any], field_confidence: dict[str, float] | None, fallback_score: int) -> dict[str, float]:
    merged: dict[str, float] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, list) and not value:
            continue
        merged[key] = float((field_confidence or {}).get(key, fallback_score))
    return merged


def prepare_record_payload(record_type: str | RecordType, values: dict[str, Any]) -> StructuredRecordPayload:
    canonical_type = normalize_record_type(record_type)
    normalized_name = normalize_name(values.get("title") or values.get("name"))
    fingerprint = build_fingerprint(normalized_name, values)
    confidence_score = int(values.get("confidence_score", 0) or 0)
    field_confidence = build_field_confidence(values, values.get("field_confidence"), confidence_score)
    return StructuredRecordPayload.from_values(
        record_type=canonical_type,
        normalized_name=normalized_name,
        fingerprint=fingerprint,
        values=values,
        field_confidence=field_confidence,
        confidence_score=confidence_score,
    )


def merge_record(existing: dict[str, Any], incoming: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    merged = dict(existing)
    existing_conf = dict(existing.get("field_confidence") or {})
    incoming_conf = dict(incoming.get("field_confidence") or {})
    merge_changes: dict[str, dict[str, Any]] = {}

    keys = set(existing.keys()) | set(incoming.keys())
    keys.discard("field_confidence")
    for key in keys:
        current = existing.get(key)
        proposed = incoming.get(key)

        if proposed is None:
            continue

        if key in ARRAY_FIELDS:
            curr_values = current if isinstance(current, list) else []
            inc_values = proposed if isinstance(proposed, list) else []
            union = list(dict.fromkeys([*curr_values, *inc_values]))
            if union != curr_values:
                merged[key] = union
                merge_changes[key] = {"before": current, "after": union, "rule": "array_union"}
            existing_conf[key] = max(float(existing_conf.get(key, 0)), float(incoming_conf.get(key, 0)))
            continue

        if current is None:
            merged[key] = proposed
            merge_changes[key] = {"before": current, "after": proposed, "rule": "fill_null"}
            existing_conf[key] = float(incoming_conf.get(key, 0))
            continue

        if current == proposed:
            existing_conf[key] = max(float(existing_conf.get(key, 0)), float(incoming_conf.get(key, 0)))
            continue

        if float(incoming_conf.get(key, 0)) > float(existing_conf.get(key, 0)):
            merged[key] = proposed
            merge_changes[key] = {"before": current, "after": proposed, "rule": "higher_confidence"}
            existing_conf[key] = float(incoming_conf.get(key, 0))

    merged["field_confidence"] = existing_conf
    return merged, merge_changes


def fuzzy_name_match(left: str, right: str, threshold: float = 0.92) -> bool:
    if not left or not right:
        return False
    return SequenceMatcher(a=left, b=right).ratio() >= threshold


def build_merge_snapshot(existing_values: dict[str, Any], incoming_values: dict[str, Any], changes: dict[str, Any]) -> str:
    return json.dumps(
        {
            "existing": existing_values,
            "incoming": incoming_values,
            "changes": changes,
        },
        default=str,
    )
