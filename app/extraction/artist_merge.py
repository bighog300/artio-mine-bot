import json
from typing import Any
from urllib.parse import urlparse

from app.extraction.completeness import compute_artist_completeness

ARTIST_RELATED_PAGE_TYPES = {
    "artist_profile",
    "artist_profile_hub",
    "artist_biography",
    "artist_exhibitions",
    "artist_articles",
    "artist_press",
    "artist_memories",
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


def merge_artist_payload(
    existing_raw_data: str | None,
    *,
    page_type: str,
    source_url: str,
    extracted_data: dict[str, Any] | None,
    related_data: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = _load_raw_data(existing_raw_data)
    source_pages = set(merged.get("source_pages", []))
    source_pages.add(source_url)

    merged.setdefault("merged_from", {})
    merged.setdefault("related", {})

    payload = dict(merged.get("artist_payload", {}))
    extracted_data = extracted_data or {}
    related_data = related_data or {}

    if extracted_data.get("name"):
        payload["artist_name"] = _pick_stronger(payload.get("artist_name"), extracted_data.get("name"))
    if extracted_data.get("bio"):
        if page_type == "artist_biography":
            payload["bio_full"] = _pick_stronger(payload.get("bio_full"), extracted_data.get("bio"))
        else:
            payload["bio_short"] = _pick_stronger(payload.get("bio_short"), extracted_data.get("bio"))
    for field, dest in (
        ("website_url", "website"),
        ("email", "email"),
        ("nationality", "nationality"),
        ("avatar_url", "avatar_url"),
    ):
        payload[dest] = _pick_stronger(payload.get(dest), extracted_data.get(field))

    image_urls = list(dict.fromkeys((payload.get("image_urls") or []) + (extracted_data.get("image_urls") or [])))
    if image_urls:
        payload["image_urls"] = image_urls

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

    merged["artist_payload"] = payload
    merged["source_pages"] = sorted(source_pages)
    merged["merged_from"][source_url] = {
        "page_type": page_type,
        "extracted_data": extracted_data,
        "related_data": related_data,
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
