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
