import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db import crud

router = APIRouter(prefix="/graph", tags=["graph"])


async def _find_record_by_title(db: AsyncSession, source_id: str, title: str, record_type: str):
    candidates = await crud.list_records(
        db,
        source_id=source_id,
        record_type=record_type,
        skip=0,
        limit=5000,
    )
    title_key = title.strip().lower()
    for candidate in candidates:
        if (candidate.title or "").strip().lower() == title_key:
            return candidate
    return None


async def _refresh_artist_relationships(db: AsyncSession, artist) -> list[dict[str, Any]]:
    payload = {}
    if artist.raw_data:
        try:
            payload = json.loads(artist.raw_data)
        except json.JSONDecodeError:
            payload = {}
    artist_payload = payload.get("artist_payload", {}) if isinstance(payload, dict) else {}

    edges: list[dict[str, Any]] = []

    for exhibition in artist_payload.get("exhibitions", []):
        title = exhibition.get("title")
        if not title:
            continue
        target = await _find_record_by_title(db, artist.source_id, title, "exhibition")
        if target is None:
            continue
        await crud.upsert_entity_relationship(
            db,
            source_id=artist.source_id,
            from_record_id=artist.id,
            to_record_id=target.id,
            relationship_type="artist_exhibition",
            metadata={"title": title, "venue": exhibition.get("venue")},
        )
        edges.append({"relationship_type": "artist_exhibition", "target_id": target.id, "target_title": target.title})

    for article in artist_payload.get("articles", []):
        title = article.get("title")
        if not title:
            continue
        target = await _find_record_by_title(db, artist.source_id, title, "artist_article")
        if target is None:
            continue
        await crud.upsert_entity_relationship(
            db,
            source_id=artist.source_id,
            from_record_id=artist.id,
            to_record_id=target.id,
            relationship_type="artist_article",
            metadata={"title": title},
        )
        edges.append({"relationship_type": "artist_article", "target_id": target.id, "target_title": target.title})

    locations = []
    if artist.nationality:
        locations.append(artist.nationality)
    if artist.city:
        locations.append(artist.city)
    if artist.country:
        locations.append(artist.country)
    dedup_locations = sorted(set(locations))
    for location_name in dedup_locations:
        await crud.upsert_entity_relationship(
            db,
            source_id=artist.source_id,
            from_record_id=artist.id,
            to_record_id=artist.id,
            relationship_type="artist_location",
            metadata={"location": location_name},
        )
        edges.append({"relationship_type": "artist_location", "target_id": artist.id, "target_title": location_name})

    return edges


@router.get("/artist/{record_id}")
async def get_artist_graph(record_id: str, db: AsyncSession = Depends(get_db)):
    artist = await crud.get_record(db, record_id)
    if artist is None or artist.record_type != "artist":
        raise HTTPException(status_code=404, detail="Artist not found")

    await _refresh_artist_relationships(db, artist)
    relationships = await crud.list_relationships_for_record(
        db,
        source_id=artist.source_id,
        record_id=artist.id,
    )

    connected_entities = []
    seen = set()
    for rel in relationships:
        target_id = rel.to_record_id if rel.from_record_id == artist.id else rel.from_record_id
        if rel.relationship_type == "artist_location":
            metadata = json.loads(rel.metadata_json) if rel.metadata_json else {}
            location = metadata.get("location")
            if location and (rel.relationship_type, location) not in seen:
                seen.add((rel.relationship_type, location))
                connected_entities.append(
                    {
                        "id": None,
                        "relationship_type": rel.relationship_type,
                        "record_type": "location",
                        "title": location,
                    }
                )
            continue
        target = await crud.get_record(db, target_id)
        if not target:
            continue
        marker = (rel.relationship_type, target.id)
        if marker in seen:
            continue
        seen.add(marker)
        connected_entities.append(
            {
                "id": target.id,
                "relationship_type": rel.relationship_type,
                "record_type": target.record_type,
                "title": target.title,
            }
        )

    exhibitions = [item for item in connected_entities if item["record_type"] == "exhibition"]
    articles = [item for item in connected_entities if item["record_type"] in {"artist_article", "artist_press"}]

    return {
        "artist": {
            "id": artist.id,
            "title": artist.title,
            "bio": artist.bio,
            "source_id": artist.source_id,
            "completeness_score": artist.completeness_score,
            "has_conflicts": artist.has_conflicts,
        },
        "exhibitions": exhibitions,
        "articles": articles,
        "connected_entities": connected_entities,
    }
