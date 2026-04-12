import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import (
    ApproveResponse,
    BulkApproveRequest,
    BulkApproveResponse,
    RecordDetailResponse,
    RecordListItem,
    RecordUpdate,
    RejectRequest,
    SetPrimaryImageRequest,
)
from app.db import crud

router = APIRouter(prefix="/records", tags=["records"])


def _to_record_list_item(record, image_count: int = 0, primary_image_url: str | None = None) -> dict:
    reasons = record.confidence_reasons
    if isinstance(reasons, str):
        try:
            reasons = json.loads(reasons)
        except Exception:
            reasons = []

    return {
        "id": record.id,
        "source_id": record.source_id,
        "record_type": record.record_type,
        "status": record.status,
        "title": record.title,
        "description": record.description,
        "confidence_score": record.confidence_score,
        "confidence_band": record.confidence_band,
        "confidence_reasons": reasons,
        "source_url": record.source_url,
        "image_count": image_count,
        "primary_image_url": primary_image_url,
        "created_at": record.created_at,
    }


@router.get("")
async def list_records(
    source_id: str | None = None,
    record_type: str | None = None,
    status: str | None = None,
    confidence_band: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    records = await crud.list_records(
        db,
        source_id=source_id,
        record_type=record_type,
        status=status,
        confidence_band=confidence_band,
        search=search,
        skip=skip,
        limit=limit,
    )
    total = await crud.count_records(db, source_id=source_id, status=status)

    items = []
    for record in records:
        images = await crud.list_images(db, record_id=record.id, limit=100)
        primary_url = None
        if record.primary_image_id:
            for img in images:
                if img.id == record.primary_image_id:
                    primary_url = img.url
                    break
        items.append(_to_record_list_item(record, len(images), primary_url))

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{record_id}")
async def get_record(record_id: str, db: AsyncSession = Depends(get_db)):
    record = await crud.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    images = await crud.list_images(db, record_id=record_id, limit=100)
    images_data = [
        {
            "id": img.id,
            "url": img.url,
            "image_type": img.image_type,
            "alt_text": img.alt_text,
            "confidence": img.confidence,
            "is_valid": img.is_valid,
            "mime_type": img.mime_type,
            "width": img.width,
            "height": img.height,
        }
        for img in images
    ]

    return RecordDetailResponse.model_validate(
        {
            **record.__dict__,
            "images": images_data,
        }
    )


@router.patch("/{record_id}")
async def update_record(
    record_id: str, body: RecordUpdate, db: AsyncSession = Depends(get_db)
):
    record = await crud.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if update_data:
        record = await crud.update_record(db, record_id, **update_data)
    return record


@router.post("/{record_id}/approve", response_model=ApproveResponse)
async def approve_record(record_id: str, db: AsyncSession = Depends(get_db)):
    record = await crud.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record = await crud.approve_record(db, record_id)
    return ApproveResponse(id=record.id, status=record.status)


@router.post("/{record_id}/reject", response_model=ApproveResponse)
async def reject_record(
    record_id: str, body: RejectRequest | None = None, db: AsyncSession = Depends(get_db)
):
    record = await crud.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    kwargs = {}
    if body and body.reason:
        kwargs["admin_notes"] = body.reason
    record = await crud.reject_record(db, record_id)
    if kwargs:
        record = await crud.update_record(db, record_id, **kwargs)
    return ApproveResponse(id=record.id, status=record.status)


@router.post("/bulk-approve", response_model=BulkApproveResponse)
async def bulk_approve(body: BulkApproveRequest, db: AsyncSession = Depends(get_db)):
    count = await crud.bulk_approve(db, body.source_id, min_confidence=body.min_confidence)
    return BulkApproveResponse(approved_count=count)


@router.post("/{record_id}/set-primary-image")
async def set_primary_image(
    record_id: str, body: SetPrimaryImageRequest, db: AsyncSession = Depends(get_db)
):
    record = await crud.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record = await crud.set_primary_image(db, record_id=record_id, image_id=body.image_id)
    return record
