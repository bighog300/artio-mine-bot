import json
from typing import Any

from app.db.models import Image, Record


def format_record(record: Record, images: list[Image] | None = None) -> dict[str, Any]:
    """Convert Record ORM object to Artio feed format."""
    if images is None:
        images = []

    def parse_json(val: str | None) -> list:
        if not val:
            return []
        try:
            return json.loads(val)
        except Exception:
            return []

    primary_image_url = None
    if record.primary_image_id:
        for img in images:
            if img.id == record.primary_image_id:
                primary_image_url = img.url
                break

    all_image_urls = [img.url for img in images if img.is_valid]

    data: dict[str, Any] = {
        "id": record.id,
        "type": record.record_type,
        "source_url": record.source_url,
    }

    # Core fields
    if record.title:
        data["title"] = record.title
    if record.description:
        data["description"] = record.description

    # Type-specific fields
    if record.record_type in ("event", "exhibition"):
        if record.start_date:
            data["start_date"] = record.start_date
        if record.end_date:
            data["end_date"] = record.end_date
        if record.venue_name:
            data["venue_name"] = record.venue_name
        if record.venue_address:
            data["venue_address"] = record.venue_address
        artist_names = parse_json(record.artist_names)
        if artist_names:
            data["artist_names"] = artist_names
        if record.record_type == "event":
            if record.ticket_url:
                data["ticket_url"] = record.ticket_url
            if record.is_free is not None:
                data["is_free"] = record.is_free
            if record.price_text:
                data["price_text"] = record.price_text
        elif record.record_type == "exhibition":
            if record.curator:
                data["curator"] = record.curator

    elif record.record_type == "artist":
        if record.bio:
            data["bio"] = record.bio
        if record.nationality:
            data["nationality"] = record.nationality
        if record.birth_year:
            data["birth_year"] = record.birth_year
        mediums = parse_json(record.mediums)
        if mediums:
            data["mediums"] = mediums
        collections = parse_json(record.collections)
        if collections:
            data["collections"] = collections
        if record.website_url:
            data["website_url"] = record.website_url
        if record.instagram_url:
            data["instagram_url"] = record.instagram_url
        if record.email:
            data["email"] = record.email
        if record.avatar_url:
            data["avatar_url"] = record.avatar_url

    elif record.record_type == "venue":
        if record.address:
            data["address"] = record.address
        if record.city:
            data["city"] = record.city
        if record.country:
            data["country"] = record.country
        if record.website_url:
            data["website_url"] = record.website_url
        if record.phone:
            data["phone"] = record.phone
        if record.email:
            data["email"] = record.email
        if record.opening_hours:
            data["opening_hours"] = record.opening_hours

    elif record.record_type == "artwork":
        if record.medium:
            data["medium"] = record.medium
        if record.year:
            data["year"] = record.year
        if record.dimensions:
            data["dimensions"] = record.dimensions
        if record.price:
            data["price"] = record.price

    # Images
    if primary_image_url:
        data["primary_image_url"] = primary_image_url
    if all_image_urls:
        data["image_urls"] = all_image_urls

    # Confidence metadata
    data["confidence_score"] = record.confidence_score
    data["confidence_band"] = record.confidence_band

    return data
