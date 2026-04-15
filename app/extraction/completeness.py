from typing import Any


def compute_artist_completeness(payload: dict[str, Any]) -> tuple[int, list[str]]:
    missing_fields: list[str] = []
    score = 0

    if payload.get("artist_name"):
        score += 20
    else:
        missing_fields.append("artist_name")

    if payload.get("bio_short") or payload.get("bio_full"):
        score += 20
    else:
        missing_fields.append("bio")

    if payload.get("website") or payload.get("email"):
        score += 15
    else:
        missing_fields.append("website_or_email")

    if payload.get("image_urls"):
        score += 10
    else:
        missing_fields.append("images")

    has_child_references = any(
        payload.get(field)
        for field in ("exhibitions", "articles", "press")
    )
    if has_child_references:
        score += 20
    else:
        missing_fields.append("exhibitions_articles_press")

    if payload.get("location") or payload.get("nationality"):
        score += 5
    else:
        missing_fields.append("location_or_nationality")

    if payload.get("source_pages"):
        score += 10
    else:
        missing_fields.append("source_pages")

    return min(score, 100), missing_fields
