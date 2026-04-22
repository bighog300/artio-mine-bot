from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from typing import Any

from app.records.schema import RecordType, StructuredRecordPayload

ARRAY_FIELDS = {"artist_names", "mediums", "collections"}
FINGERPRINT_VERSION = "v2"
KEY_FINGERPRINT_FIELDS = (
    "title",
    "start_date",
    "end_date",
    "venue_name",
    "birth_year",
    "city",
    "country",
)
TYPE_SECONDARY_FIELDS: dict[RecordType, tuple[str, ...]] = {
    RecordType.ARTIST: ("birth_year", "website_url", "instagram_url", "email", "nationality"),
    RecordType.VENUE: ("address", "city", "country", "phone", "website_url"),
    RecordType.EVENT: ("start_date", "end_date", "venue_name", "ticket_url", "source_url"),
    RecordType.EXHIBITION: ("start_date", "end_date", "venue_name", "curator", "source_url"),
    RecordType.ARTWORK: ("year", "medium", "dimensions", "price", "source_url"),
}
TYPE_STRONG_SIGNAL_FIELDS: dict[RecordType, tuple[str, ...]] = {
    RecordType.ARTIST: ("website_url", "instagram_url", "email", "birth_year"),
    RecordType.VENUE: ("address", "phone", "website_url"),
    RecordType.EVENT: ("ticket_url", "source_url"),
    RecordType.EXHIBITION: ("source_url", "venue_name"),
    RecordType.ARTWORK: ("source_url", "dimensions", "year"),
}


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


def _normalize_fingerprint_value(value: Any) -> Any:
    if isinstance(value, list):
        return sorted(str(v).strip().lower() for v in value if v is not None and str(v).strip())
    if isinstance(value, str):
        return value.strip().lower()
    return value


def build_fingerprint(record_type: RecordType, normalized_name: str, values: dict[str, Any]) -> str:
    type_fields = TYPE_SECONDARY_FIELDS.get(record_type, ())
    selected_fields = list(dict.fromkeys([*KEY_FINGERPRINT_FIELDS, *type_fields]))
    canonical_payload: dict[str, Any] = {
        "fingerprint_version": FINGERPRINT_VERSION,
        "record_type": record_type.value,
        "normalized_name": normalized_name,
        "fields": {},
    }
    for field in selected_fields:
        value = values.get(field)
        if value is None:
            continue
        canonical_payload["fields"][field] = _normalize_fingerprint_value(value)
    serialized = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_field_confidence(values: dict[str, Any], field_confidence: dict[str, float] | None, fallback_score: int) -> dict[str, float]:
    merged: dict[str, float] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, list) and not value:
            continue
        merged[key] = float((field_confidence or {}).get(key, fallback_score))
    return merged


def _coerce_payload_values(values: dict[str, Any]) -> dict[str, Any]:
    coerced = {key: value for key, value in values.items() if not key.startswith("_")}
    for field in ARRAY_FIELDS:
        value = coerced.get(field)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    coerced[field] = parsed
            except json.JSONDecodeError:
                continue
    return coerced


def prepare_record_payload(record_type: str | RecordType, values: dict[str, Any]) -> StructuredRecordPayload:
    canonical_type = normalize_record_type(record_type)
    normalized_values = _coerce_payload_values(values)
    normalized_name = normalize_name(normalized_values.get("title") or normalized_values.get("name"))
    fingerprint = build_fingerprint(canonical_type, normalized_name, normalized_values)
    confidence_score = int(normalized_values.get("confidence_score", 0) or 0)
    field_confidence = build_field_confidence(normalized_values, normalized_values.get("field_confidence"), confidence_score)
    return StructuredRecordPayload.from_values(
        record_type=canonical_type,
        normalized_name=normalized_name,
        fingerprint=fingerprint,
        fingerprint_version=FINGERPRINT_VERSION,
        values=normalized_values,
        field_confidence=field_confidence,
        confidence_score=confidence_score,
    )


def merge_record(existing: dict[str, Any], incoming: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    merged = dict(existing)
    existing_conf = dict(existing.get("field_confidence") or {})
    incoming_conf = dict(incoming.get("field_confidence") or {})
    existing_provenance = dict(existing.get("field_provenance") or {})
    incoming_page_id = incoming.get("page_id")
    merge_changes: dict[str, dict[str, Any]] = {}
    conflicts: dict[str, list[dict[str, Any]]] = dict(existing.get("conflicts") or {})

    keys = set(existing.keys()) | set(incoming.keys())
    keys -= {"field_confidence", "field_provenance", "conflicts"}
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
            existing_provenance[key] = {
                "value": union,
                "source": incoming_page_id,
                "confidence": existing_conf[key],
            }
            continue

        if current is None:
            merged[key] = proposed
            merge_changes[key] = {"before": current, "after": proposed, "rule": "fill_null"}
            existing_conf[key] = float(incoming_conf.get(key, 0))
            existing_provenance[key] = {
                "value": proposed,
                "source": incoming_page_id,
                "confidence": existing_conf[key],
            }
            continue

        if current == proposed:
            existing_conf[key] = max(float(existing_conf.get(key, 0)), float(incoming_conf.get(key, 0)))
            existing_provenance[key] = {
                "value": current,
                "source": existing_provenance.get(key, {}).get("source"),
                "confidence": existing_conf[key],
            }
            continue

        current_conf = float(existing_conf.get(key, 0))
        proposed_conf = float(incoming_conf.get(key, 0))
        if current_conf >= 80 and proposed_conf >= 80:
            conflicts.setdefault(key, [])
            conflicts[key].append({"value": current, "source": existing_provenance.get(key, {}).get("source"), "confidence": current_conf, "selected": True})
            conflicts[key].append({"value": proposed, "source": incoming_page_id, "confidence": proposed_conf, "selected": False})
            merge_changes[key] = {"before": current, "after": current, "rule": "high_conflict_no_overwrite"}
            continue

        if proposed_conf > current_conf:
            merged[key] = proposed
            merge_changes[key] = {"before": current, "after": proposed, "rule": "higher_confidence"}
            existing_conf[key] = proposed_conf
            existing_provenance[key] = {"value": proposed, "source": incoming_page_id, "confidence": proposed_conf}

    merged["field_confidence"] = existing_conf
    merged["field_provenance"] = existing_provenance
    merged["conflicts"] = conflicts
    merged["has_conflicts"] = bool(conflicts)
    return merged, merge_changes


def fuzzy_name_match(left: str, right: str, threshold: float = 0.92) -> bool:
    if not left or not right:
        return False
    return SequenceMatcher(a=left, b=right).ratio() >= threshold


def similarity_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(a=left, b=right).ratio()


def _field_overlap_score(
    existing_values: dict[str, Any],
    incoming_values: dict[str, Any],
    fields: tuple[str, ...],
    strong_signal_fields: tuple[str, ...],
) -> tuple[float, bool, list[str]]:
    matches = 0
    compared = 0
    strong_signal = False
    matched_fields: list[str] = []
    for field in fields:
        left = existing_values.get(field)
        right = incoming_values.get(field)
        if left is None or right is None:
            continue
        compared += 1
        left_norm = _normalize_fingerprint_value(left)
        right_norm = _normalize_fingerprint_value(right)
        if left_norm == right_norm:
            matches += 1
            matched_fields.append(field)
            if field in strong_signal_fields:
                strong_signal = True
    if compared == 0:
        return 0.0, False, []
    return matches / compared, strong_signal, matched_fields


def classify_identity_match(
    *,
    record_type: RecordType,
    existing_values: dict[str, Any],
    incoming_values: dict[str, Any],
) -> tuple[float, str, dict[str, Any]]:
    name_score = similarity_score(existing_values.get("normalized_name", ""), incoming_values.get("normalized_name", ""))
    strong_signal_fields = TYPE_STRONG_SIGNAL_FIELDS.get(record_type, ())
    overlap_score, has_strong_secondary, matched_secondary_fields = _field_overlap_score(
        existing_values,
        incoming_values,
        TYPE_SECONDARY_FIELDS.get(record_type, ()),
        strong_signal_fields,
    )
    total_score = (name_score * 0.75) + (overlap_score * 0.25)
    if total_score >= 0.85 and has_strong_secondary:
        decision = "merge"
    elif total_score >= 0.7:
        decision = "review"
    else:
        decision = "new"
    return total_score, decision, {
        "name_similarity": round(name_score, 6),
        "secondary_overlap": round(overlap_score, 6),
        "strong_secondary_signal": has_strong_secondary,
        "strong_signal_fields": list(strong_signal_fields),
        "matched_secondary_fields": matched_secondary_fields,
    }


def build_merge_snapshot(existing_values: dict[str, Any], incoming_values: dict[str, Any], changes: dict[str, Any]) -> str:
    return json.dumps(
        {
            "merge_event": "deduplication_merge",
            "involved_record_ids": {
                "primary": existing_values.get("id"),
                "secondary": incoming_values.get("id") or f"incoming:{incoming_values.get('fingerprint', '')}",
            },
            "before": existing_values,
            "after": {**existing_values, **{k: v.get("after") for k, v in changes.items()}},
            "existing": existing_values,
            "incoming": incoming_values,
            "changes": changes,
        },
        default=str,
    )
