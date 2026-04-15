import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import ExportPreviewByType, ExportPreviewResponse, ExportPushRequest, ExportPushResponse
from app.config import settings
from app.db import crud
from app.db.models import Record

router = APIRouter(prefix="/export", tags=["export"])


def _parse_raw_data(raw_data: str | None) -> dict:
    if not raw_data:
        return {}
    try:
        parsed = json.loads(raw_data)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _clean_artist_export(record: Record, include_provenance: bool = False) -> dict:
    raw = _parse_raw_data(record.raw_data)
    artist_payload = raw.get("artist_payload", {}) if isinstance(raw, dict) else {}
    output = {
        "id": record.id,
        "artist_name": record.title or artist_payload.get("artist_name"),
        "bio": record.bio or artist_payload.get("bio_full") or artist_payload.get("bio_short"),
        "nationality": record.nationality or artist_payload.get("nationality"),
        "website_url": record.website_url or artist_payload.get("website"),
        "completeness_score": record.completeness_score,
        "exhibitions": artist_payload.get("exhibitions", []),
        "articles": artist_payload.get("articles", []),
    }
    if include_provenance:
        output["provenance"] = raw.get("provenance") or raw.get("artist_payload_provenance") or {}
    return output


def _clean_exhibition_export(record: Record) -> dict:
    return {
        "id": record.id,
        "title": record.title,
        "description": record.description,
        "start_date": record.start_date,
        "end_date": record.end_date,
        "venue_name": record.venue_name,
        "venue_address": record.venue_address,
        "artist_names": json.loads(record.artist_names or "[]"),
        "source_url": record.source_url,
    }


@router.get("/preview", response_model=ExportPreviewResponse)
async def get_export_preview(
    source_id: str | None = None, db: AsyncSession = Depends(get_db)
):
    stmt = select(func.count(Record.id)).where(
        Record.status == "approved", Record.exported_at.is_(None)
    )
    if source_id:
        stmt = stmt.where(Record.source_id == source_id)
    total = (await db.execute(stmt)).scalar_one()

    by_type = ExportPreviewByType()
    for rtype in ("artist", "event", "exhibition", "venue", "artwork"):
        stmt2 = select(func.count(Record.id)).where(
            Record.status == "approved",
            Record.exported_at.is_(None),
            Record.record_type == rtype,
        )
        if source_id:
            stmt2 = stmt2.where(Record.source_id == source_id)
        count = (await db.execute(stmt2)).scalar_one()
        setattr(by_type, rtype, count)

    return ExportPreviewResponse(
        record_count=total,
        by_type=by_type,
        artio_configured=bool(settings.artio_api_url and settings.artio_api_key),
    )


@router.post("/push", response_model=ExportPushResponse)
async def push_to_artio(body: ExportPushRequest, db: AsyncSession = Depends(get_db)):
    from app.export.artio_client import ArtioClient
    from app.export.formatter import format_record

    if not settings.artio_api_url or not settings.artio_api_key:
        raise HTTPException(
            status_code=400, detail="Artio API not configured. Set ARTIO_API_URL and ARTIO_API_KEY."
        )

    # Fetch records to export
    if body.record_ids:
        records = []
        for rid in body.record_ids:
            record = await crud.get_record(db, rid)
            if record and record.status == "approved":
                records.append(record)
    else:
        stmt = select(Record).where(
            Record.status == "approved", Record.exported_at.is_(None)
        )
        if body.source_id:
            stmt = stmt.where(Record.source_id == body.source_id)
        result = await db.execute(stmt)
        records = list(result.scalars().all())

    if not records:
        return ExportPushResponse(exported_count=0, failed_count=0)

    # Format records
    formatted = []
    for record in records:
        images = await crud.list_images(db, record_id=record.id, limit=100)
        formatted.append(format_record(record, images))

    # Push to Artio
    client = ArtioClient()
    export_result = await client.push_records(formatted)

    # Mark exported records
    exported_ids = set(export_result.exported)
    for record in records:
        if record.id in exported_ids:
            await crud.update_record(
                db, record.id, status="exported", exported_at=datetime.now(UTC)
            )

    return ExportPushResponse(
        exported_count=len(export_result.exported),
        failed_count=len(export_result.failed),
        errors=[f["error"] for f in export_result.failed if "error" in f],
    )


@router.get("/history")
async def get_export_history(
    source_id: str | None = None, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    stmt = select(Record).where(Record.status == "exported")
    if source_id:
        stmt = stmt.where(Record.source_id == source_id)
    stmt = stmt.order_by(Record.exported_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    items = [
        {
            "id": r.id,
            "title": r.title,
            "record_type": r.record_type,
            "exported_at": r.exported_at,
            "status": r.status,
        }
        for r in records
    ]
    return {"items": items, "total": len(items), "skip": skip, "limit": limit}


@router.get("/artists")
async def export_artists(
    source_id: str | None = None,
    include_provenance: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    artists = await crud.list_records(
        db,
        source_id=source_id,
        record_type="artist",
        skip=skip,
        limit=limit,
    )
    items = [_clean_artist_export(artist, include_provenance=include_provenance) for artist in artists]
    total = await crud.count_records(db, source_id=source_id, record_type="artist")
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/artists/{record_id}")
async def export_artist_by_id(
    record_id: str,
    include_provenance: bool = False,
    db: AsyncSession = Depends(get_db),
):
    artist = await crud.get_record(db, record_id)
    if artist is None or artist.record_type != "artist":
        raise HTTPException(status_code=404, detail="Artist not found")
    return _clean_artist_export(artist, include_provenance=include_provenance)


@router.get("/exhibitions")
async def export_exhibitions(
    source_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    exhibitions = await crud.list_records(
        db,
        source_id=source_id,
        record_type="exhibition",
        skip=skip,
        limit=limit,
    )
    total = await crud.count_records(db, source_id=source_id, record_type="exhibition")
    return {
        "items": [_clean_exhibition_export(item) for item in exhibitions],
        "total": total,
        "skip": skip,
        "limit": limit,
    }
