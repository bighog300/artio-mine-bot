import json


def score_record(
    record_type: str, data: dict, image_urls: list[str]
) -> tuple[int, str, list[str]]:
    """
    Score a record 0–100 based on completeness signals.
    Returns (score, band, reasons).
    """
    score = 0
    reasons: list[str] = []

    # +20: Title or name present
    has_title = bool(data.get("title") or data.get("name"))
    if has_title:
        score += 20
        reasons.append("name present" if "name" in data else "title present")

    # +15: Description or bio present
    has_description = bool(data.get("description") or data.get("bio"))
    if has_description:
        score += 15
        reasons.append("bio present" if data.get("bio") else "description present")

    # +15: At least one date (for events/exhibitions)
    if record_type in ("event", "exhibition"):
        has_date = bool(data.get("start_date") or data.get("end_date"))
        if has_date:
            score += 15
            reasons.append("date present")

    # +10: Venue name present
    has_venue = bool(data.get("venue_name"))
    if has_venue:
        score += 10
        reasons.append("venue present")

    # +10: At least one artist linked
    artist_names = data.get("artist_names", [])
    if isinstance(artist_names, str):
        try:
            artist_names = json.loads(artist_names)
        except Exception:
            artist_names = []
    has_artists = bool(artist_names)
    if has_artists:
        score += 10
        reasons.append("artists linked")

    # +15: At least one valid image URL
    all_image_urls = image_urls or data.get("image_urls", [])
    if isinstance(all_image_urls, str):
        try:
            all_image_urls = json.loads(all_image_urls)
        except Exception:
            all_image_urls = []
    has_image = bool(all_image_urls)
    if has_image:
        score += 15
        reasons.append("avatar image found" if record_type == "artist" else "image found")

    # +10: JSON-LD source (indicated by raw_data having jsonld marker or high confidence from source)
    has_jsonld = data.get("_jsonld_source", False)
    if has_jsonld:
        score += 10
        reasons.append("JSON-LD source")

    # +5: AI extracted with high model confidence
    ai_confidence = data.get("_ai_confidence", 0)
    if isinstance(ai_confidence, (int, float)) and ai_confidence >= 80:
        score += 5
        reasons.append("high AI confidence")

    # Cap at 100
    score = min(score, 100)

    # Determine band
    if score >= 70:
        band = "HIGH"
    elif score >= 40:
        band = "MEDIUM"
    else:
        band = "LOW"

    return score, band, reasons
