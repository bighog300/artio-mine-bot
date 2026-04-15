import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db import crud

router = APIRouter(prefix="/search", tags=["search"])


def _parse_json_field(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _exhibition_count(record) -> int:
    payload = _parse_json_field(record.raw_data)
    artist_payload = payload.get("artist_payload", {}) if isinstance(payload, dict) else {}
    exhibitions = artist_payload.get("exhibitions") or payload.get("related", {}).get("exhibitions") or []
    return len(exhibitions)


@router.get("/artists")
async def search_artists(
    q: str | None = None,
    completeness_score: int | None = None,
    location: str | None = None,
    has_exhibitions: bool | None = None,
    has_articles: bool | None = None,
    has_conflicts: bool | None = None,
    sort: str = "completeness",
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    records = await crud.search_records(
        db,
        record_type="artist",
        query=q,
        location=location,
        min_completeness_score=completeness_score,
        has_exhibitions=has_exhibitions,
        has_articles=has_articles,
        has_conflicts=has_conflicts,
        sort_by="alphabetical" if sort == "alphabetical" else "completeness",
        skip=skip,
        limit=limit,
    )
    if sort == "number_of_exhibitions":
        records = sorted(records, key=_exhibition_count, reverse=True)

    total = await crud.count_search_records(
        db,
        record_type="artist",
        query=q,
        location=location,
        min_completeness_score=completeness_score,
        has_exhibitions=has_exhibitions,
        has_articles=has_articles,
        has_conflicts=has_conflicts,
    )

    items = [
        {
            "id": record.id,
            "source_id": record.source_id,
            "name": record.title,
            "bio": record.bio,
            "location": ", ".join([x for x in [record.city, record.country, record.nationality] if x]) or None,
            "completeness_score": record.completeness_score,
            "has_conflicts": record.has_conflicts,
            "has_exhibitions": _exhibition_count(record) > 0,
            "has_articles": '"articles"' in (record.raw_data or ""),
            "number_of_exhibitions": _exhibition_count(record),
        }
        for record in records
    ]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/exhibitions")
async def search_exhibitions(
    q: str | None = None,
    location: str | None = None,
    sort: str = "alphabetical",
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    records = await crud.search_records(
        db,
        record_type="exhibition",
        query=q,
        location=location,
        sort_by="alphabetical" if sort == "alphabetical" else "completeness",
        skip=skip,
        limit=limit,
    )
    total = await crud.count_search_records(
        db,
        record_type="exhibition",
        query=q,
        location=location,
    )
    items = [
        {
            "id": record.id,
            "source_id": record.source_id,
            "title": record.title,
            "description": record.description,
            "venue_name": record.venue_name,
            "venue_address": record.venue_address,
            "start_date": record.start_date,
            "end_date": record.end_date,
            "completeness_score": record.completeness_score,
        }
        for record in records
    ]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/articles")
async def search_articles(
    q: str | None = None,
    sort: str = "alphabetical",
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    records = await crud.search_records(
        db,
        record_type="artist_article",
        query=q,
        sort_by="alphabetical" if sort == "alphabetical" else "completeness",
        skip=skip,
        limit=limit,
    )
    total = await crud.count_search_records(
        db,
        record_type="artist_article",
        query=q,
    )
    items = [
        {
            "id": record.id,
            "source_id": record.source_id,
            "title": record.title,
            "description": record.description,
            "source_url": record.source_url,
            "completeness_score": record.completeness_score,
        }
        for record in records
    ]
    return {"items": items, "total": total, "skip": skip, "limit": limit}
