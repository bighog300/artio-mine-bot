from __future__ import annotations

import json
from urllib.parse import urlparse


_DETAIL_KEYWORDS = {
    "artist": "artist_profile",
    "artists": "artist_profile",
    "event": "event_detail",
    "events": "event_detail",
    "exhibition": "exhibition_detail",
    "exhibitions": "exhibition_detail",
    "venue": "venue_profile",
    "venues": "venue_profile",
    "artwork": "artwork_detail",
    "artworks": "artwork_detail",
}
_UTILITY_KEYWORDS = {"privacy", "terms", "cookie", "cookies", "login", "account", "contact", "about"}


def predict_page_type(url: str, structure_map: str | None = None) -> str:
    path = (urlparse(url).path or "").lower()
    if structure_map:
        hinted = _predict_with_structure_map(url, structure_map)
        if hinted:
            return hinted

    for keyword, page_type in _DETAIL_KEYWORDS.items():
        if f"/{keyword}" in path:
            return page_type
    for utility in _UTILITY_KEYWORDS:
        if f"/{utility}" in path:
            return "utility"
    return "generic"


def score_url(url: str, structure_map: str | None = None) -> tuple[int, str]:
    page_type = predict_page_type(url, structure_map)
    if page_type in {"artist_profile", "event_detail", "exhibition_detail", "venue_profile", "artwork_detail"}:
        return (80, page_type)
    if page_type == "utility":
        return (5, page_type)
    if page_type == "generic":
        return (30, page_type)
    return (50, page_type)


def _predict_with_structure_map(url: str, structure_map: str) -> str | None:
    try:
        payload = json.loads(structure_map)
    except json.JSONDecodeError:
        return None
    path = (urlparse(url).path or "").lower()
    for target in payload.get("crawl_targets", []):
        page_type = target.get("page_type")
        pattern = (target.get("url_pattern") or "").lower()
        if not page_type or not pattern:
            continue
        token = pattern.split("[")[0].rstrip("/")
        if token and token in path:
            return str(page_type)
    return None
