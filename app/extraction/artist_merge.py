import json
from typing import Any
from urllib.parse import urlparse

from app.extraction.completeness import compute_artist_completeness
from app.extraction.provenance import utc_now_iso, values_conflict

ARTIST_RELATED_PAGE_TYPES = {
    "artist_profile",
    "artist_profile_hub",
    "artist_biography",
    "artist_exhibitions",
    "artist_articles",
    "artist_press",
    "artist_memories",
}


PROVENANCE_FIELD_MAP = {
    "artist_name": "name",
    "bio_short": "bio",
    "bio_full": "bio",
    "website": "website_url",
    "email": "email",
    "nationality": "nationality",
    "avatar_url": "avatar_url",
    "birth_year": "birth_year",
    "image_urls": "image_urls",
    "bio_about": "about",
    "contact_phone": "phone",
    "news_items": "news_items",
    "linked_images": "linked_images",
    "discarded_images": "discarded_images",
    "child_pages": "child_pages",
    "source_profile_url": "source_profile_url",
    "art_classes": "art_classes",
}


def derive_artist_family_key(url: str) -> str | None:
    parsed = urlparse(url)
    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        return None
    first = segments[0].lower()
    if first.endswith(".php"):
        return None
    return f"{parsed.netloc.lower()}::{first}"


def _load_raw_data(raw_data: str | None) -> dict[str, Any]:
    if not raw_data:
        return {}
    try:
        data = json.loads(raw_data)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        return {}
    return {}


def _pick_stronger(existing: Any, candidate: Any) -> Any:
    if candidate in (None, "", []):
        return existing
    if existing in (None, "", []):
        return candidate
    if isinstance(existing, str) and isinstance(candidate, str):
        return candidate if len(candidate.strip()) > len(existing.strip()) else existing
    return existing


def _source_entry(
    *,
    source_url: str,
    source_page_id: str | None,
    extraction_type: str,
    timestamp: str,
) -> dict[str, Any]:
    return {
        "source_url": source_url,
        "source_page_id": source_page_id,
        "extraction_type": extraction_type,
        "page_type": extraction_type,
        "timestamp": timestamp,
    }


def _append_provenance(
    provenance: dict[str, Any],
    *,
    field: str,
    value: Any,
    source_url: str,
    source_page_id: str | None,
    extraction_type: str,
    timestamp: str,
) -> None:
    node = provenance.setdefault(field, {"value": value, "sources": []})
    node["value"] = value
    sources = node.setdefault("sources", [])
    source = _source_entry(
        source_url=source_url,
        source_page_id=source_page_id,
        extraction_type=extraction_type,
        timestamp=timestamp,
    )
    if not any(
        s.get("source_url") == source_url
        and s.get("source_page_id") == source_page_id
        and s.get("extraction_type") == extraction_type
        for s in sources
    ):
        sources.append(source)


def _update_field_with_provenance(
    payload: dict[str, Any],
    provenance: dict[str, Any],
    conflicts: dict[str, Any],
    *,
    field: str,
    candidate: Any,
    source_url: str,
    source_page_id: str | None,
    extraction_type: str,
    timestamp: str,
) -> None:
    if candidate in (None, "", []):
        return

    existing = payload.get(field)
    selected = _pick_stronger(existing, candidate)

    if values_conflict(existing, candidate):
        conflict_entries = conflicts.setdefault(field, [])
        entries_by_value = {json.dumps(item.get("value"), sort_keys=True): item for item in conflict_entries}

        for value, from_url, from_page_id in (
            (existing, provenance.get(field, {}).get("sources", [{}])[0].get("source_url") if provenance.get(field) else source_url, provenance.get(field, {}).get("sources", [{}])[0].get("source_page_id") if provenance.get(field) else source_page_id),
            (candidate, source_url, source_page_id),
        ):
            key = json.dumps(value, sort_keys=True)
            if key not in entries_by_value:
                entries_by_value[key] = {
                    "value": value,
                    "source": from_url,
                    "source_url": from_url,
                    "source_page_id": from_page_id,
                    "extraction_type": extraction_type,
                    "timestamp": timestamp,
                    "selected": value == selected,
                    "resolved": False,
                }
            else:
                entries_by_value[key]["selected"] = value == selected

        conflicts[field] = list(entries_by_value.values())

    payload[field] = selected
    _append_provenance(
        provenance,
        field=field,
        value=selected,
        source_url=source_url,
        source_page_id=source_page_id,
        extraction_type=extraction_type,
        timestamp=timestamp,
    )


def merge_artist_payload(
    existing_raw_data: str | None,
    *,
    page_type: str,
    source_url: str,
    source_page_id: str | None = None,
    extracted_data: dict[str, Any] | None,
    related_data: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = _load_raw_data(existing_raw_data)
    source_pages = set(merged.get("source_pages", []))
    source_pages.add(source_url)
    timestamp = utc_now_iso()

    merged.setdefault("merged_from", {})
    merged.setdefault("related", {})
    conflicts = merged.setdefault("conflicts", {})
    provenance = merged.setdefault("provenance", {})

    payload = dict(merged.get("artist_payload", {}))
    extracted_data = extracted_data or {}
    related_data = related_data or {}

    payload.setdefault("news_items", [])
    payload.setdefault("linked_images", [])
    payload.setdefault("discarded_images", [])
    payload.setdefault("child_pages", [])

    if extracted_data.get("name"):
        _update_field_with_provenance(
            payload,
            provenance,
            conflicts,
            field="artist_name",
            candidate=extracted_data.get("name"),
            source_url=source_url,
            source_page_id=source_page_id,
            extraction_type=page_type,
            timestamp=timestamp,
        )

    if extracted_data.get("bio"):
        bio_field = "bio_full" if page_type == "artist_biography" else "bio_short"
        if page_type == "artist_biography":
            payload[bio_field] = extracted_data.get("bio")
            _append_provenance(
                provenance,
                field=bio_field,
                value=extracted_data.get("bio"),
                source_url=source_url,
                source_page_id=source_page_id,
                extraction_type=page_type,
                timestamp=timestamp,
            )
        else:
            _update_field_with_provenance(
                payload,
                provenance,
                conflicts,
                field=bio_field,
                candidate=extracted_data.get("bio"),
                source_url=source_url,
                source_page_id=source_page_id,
                extraction_type=page_type,
                timestamp=timestamp,
            )
    if extracted_data.get("about"):
        _update_field_with_provenance(
            payload,
            provenance,
            conflicts,
            field="bio_about",
            candidate=extracted_data.get("about"),
            source_url=source_url,
            source_page_id=source_page_id,
            extraction_type=page_type,
            timestamp=timestamp,
        )
    if extracted_data.get("phone"):
        _update_field_with_provenance(
            payload,
            provenance,
            conflicts,
            field="contact_phone",
            candidate=extracted_data.get("phone"),
            source_url=source_url,
            source_page_id=source_page_id,
            extraction_type=page_type,
            timestamp=timestamp,
        )

    for field, dest in (
        ("website_url", "website"),
        ("email", "email"),
        ("nationality", "nationality"),
        ("avatar_url", "avatar_url"),
        ("birth_year", "birth_year"),
    ):
        _update_field_with_provenance(
            payload,
            provenance,
            conflicts,
            field=dest,
            candidate=extracted_data.get(field),
            source_url=source_url,
            source_page_id=source_page_id,
            extraction_type=page_type,
            timestamp=timestamp,
        )

    image_urls = list(dict.fromkeys((payload.get("image_urls") or []) + (extracted_data.get("image_urls") or [])))
    if image_urls:
        payload["image_urls"] = image_urls
        _append_provenance(
            provenance,
            field="image_urls",
            value=image_urls,
            source_url=source_url,
            source_page_id=source_page_id,
            extraction_type=page_type,
            timestamp=timestamp,
        )

    for field in ("exhibitions", "articles", "press", "memories"):
        items = related_data.get(field) or []
        if items:
            existing_items = payload.get(field) or []
            combined = existing_items + items
            deduped: list[dict[str, Any]] = []
            seen = set()
            for item in combined:
                marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if marker in seen:
                    continue
                seen.add(marker)
                deduped.append(item)
            payload[field] = deduped
            merged["related"][field] = deduped
            _append_provenance(
                provenance,
                field=field,
                value=deduped,
                source_url=source_url,
                source_page_id=source_page_id,
                extraction_type=page_type,
                timestamp=timestamp,
            )
    for list_field in ("news_items", "linked_images", "discarded_images", "child_pages", "art_classes"):
        items = extracted_data.get(list_field) or []
        if not isinstance(items, list) or not items:
            continue
        existing_items = payload.get(list_field) or []
        deduped: list[Any] = []
        seen = set()
        for item in [*existing_items, *items]:
            marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(item)
        payload[list_field] = deduped
        _append_provenance(
            provenance,
            field=list_field,
            value=deduped,
            source_url=source_url,
            source_page_id=source_page_id,
            extraction_type=page_type,
            timestamp=timestamp,
        )

    if page_type == "artist_profile_hub":
        _update_field_with_provenance(
            payload,
            provenance,
            conflicts,
            field="source_profile_url",
            candidate=source_url,
            source_url=source_url,
            source_page_id=source_page_id,
            extraction_type=page_type,
            timestamp=timestamp,
        )

    merged["artist_payload"] = payload
    merged["source_pages"] = sorted(source_pages)
    merged["merged_from"][source_url] = {
        "page_type": page_type,
        "source_page_id": source_page_id,
        "timestamp": timestamp,
        "extracted_data": extracted_data,
        "related_data": related_data,
    }

    # Compatibility extension: nested payload representation retaining existing flat keys.
    merged["artist_payload_provenance"] = {
        field: {
            "value": payload.get(field),
            "sources": provenance.get(field, {}).get("sources", []),
        }
        for field in payload
    }

    score, missing_fields = compute_artist_completeness(
        {
            **payload,
            "source_pages": merged["source_pages"],
        }
    )
    merged["completeness_score"] = score
    merged["missing_fields"] = missing_fields
    return merged
