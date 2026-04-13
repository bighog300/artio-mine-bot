import json
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Image, Job, Page, Record, Source

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Source CRUD
# ---------------------------------------------------------------------------


async def create_source(db: AsyncSession, url: str, name: str | None = None) -> Source:
    source = Source(url=url, name=name)
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


async def get_source(db: AsyncSession, source_id: str) -> Source | None:
    result = await db.execute(select(Source).where(Source.id == source_id))
    return result.scalar_one_or_none()


async def get_source_by_url(db: AsyncSession, url: str) -> Source | None:
    result = await db.execute(select(Source).where(Source.url == url))
    return result.scalar_one_or_none()


async def list_sources(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[Source]:
    result = await db.execute(select(Source).offset(skip).limit(limit))
    return list(result.scalars().all())


async def update_source(db: AsyncSession, source_id: str, **kwargs: Any) -> Source:
    source = await get_source(db, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")
    for key, value in kwargs.items():
        setattr(source, key, value)
    source.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(source)
    return source


async def delete_source(db: AsyncSession, source_id: str) -> bool:
    source = await get_source(db, source_id)
    if source is None:
        return False
    await db.delete(source)
    await db.commit()
    return True


async def get_source_stats(db: AsyncSession, source_id: str) -> dict[str, Any]:
    pending = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.status == "pending"
        )
    )
    approved = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.status == "approved"
        )
    )
    rejected = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.status == "rejected"
        )
    )
    high = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.confidence_band == "HIGH"
        )
    )
    medium = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.confidence_band == "MEDIUM"
        )
    )
    low = await db.execute(
        select(func.count(Record.id)).where(
            Record.source_id == source_id, Record.confidence_band == "LOW"
        )
    )
    return {
        "pending_records": pending.scalar_one(),
        "approved_records": approved.scalar_one(),
        "rejected_records": rejected.scalar_one(),
        "high_confidence": high.scalar_one(),
        "medium_confidence": medium.scalar_one(),
        "low_confidence": low.scalar_one(),
    }


# ---------------------------------------------------------------------------
# Page CRUD
# ---------------------------------------------------------------------------


async def create_page(db: AsyncSession, source_id: str, url: str, **kwargs: Any) -> Page:
    original_url = kwargs.pop("original_url", url)
    page = Page(source_id=source_id, url=url, original_url=original_url, **kwargs)
    db.add(page)
    await db.commit()
    await db.refresh(page)
    return page


async def get_page(db: AsyncSession, page_id: str) -> Page | None:
    result = await db.execute(select(Page).where(Page.id == page_id))
    return result.scalar_one_or_none()


async def get_or_create_page(db: AsyncSession, source_id: str, url: str) -> tuple[Page, bool]:
    result = await db.execute(
        select(Page).where(Page.source_id == source_id, Page.url == url)
    )
    page = result.scalar_one_or_none()
    if page is not None:
        return page, False
    page = await create_page(db, source_id=source_id, url=url)
    return page, True


async def list_pages(
    db: AsyncSession,
    source_id: str | None = None,
    status: str | None = None,
    page_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Page]:
    stmt = select(Page)
    if source_id:
        stmt = stmt.where(Page.source_id == source_id)
    if status:
        stmt = stmt.where(Page.status == status)
    if page_type:
        stmt = stmt.where(Page.page_type == page_type)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_page(db: AsyncSession, page_id: str, **kwargs: Any) -> Page:
    page = await get_page(db, page_id)
    if page is None:
        raise ValueError(f"Page {page_id} not found")
    for key, value in kwargs.items():
        setattr(page, key, value)
    await db.commit()
    await db.refresh(page)
    return page


async def count_pages(db: AsyncSession, source_id: str, status: str | None = None) -> int:
    stmt = select(func.count(Page.id)).where(Page.source_id == source_id)
    if status:
        stmt = stmt.where(Page.status == status)
    result = await db.execute(stmt)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Record CRUD
# ---------------------------------------------------------------------------


async def create_record(
    db: AsyncSession, source_id: str, record_type: str, **kwargs: Any
) -> Record:
    # Serialize list fields to JSON strings
    for field in ("artist_names", "mediums", "collections", "confidence_reasons"):
        if field in kwargs and isinstance(kwargs[field], list):
            kwargs[field] = json.dumps(kwargs[field])
    record = Record(source_id=source_id, record_type=record_type, **kwargs)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_record(db: AsyncSession, record_id: str) -> Record | None:
    result = await db.execute(select(Record).where(Record.id == record_id))
    return result.scalar_one_or_none()


async def list_records(
    db: AsyncSession,
    source_id: str | None = None,
    record_type: str | None = None,
    status: str | None = None,
    confidence_band: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Record]:
    stmt = select(Record)
    if source_id:
        stmt = stmt.where(Record.source_id == source_id)
    if record_type:
        stmt = stmt.where(Record.record_type == record_type)
    if status:
        stmt = stmt.where(Record.status == status)
    if confidence_band:
        stmt = stmt.where(Record.confidence_band == confidence_band)
    if search:
        stmt = stmt.where(Record.title.ilike(f"%{search}%"))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_record(db: AsyncSession, record_id: str, **kwargs: Any) -> Record:
    record = await get_record(db, record_id)
    if record is None:
        raise ValueError(f"Record {record_id} not found")
    for key, value in kwargs.items():
        if key in ("artist_names", "mediums", "collections", "confidence_reasons") and isinstance(
            value, list
        ):
            value = json.dumps(value)
        setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(record)
    return record


async def approve_record(db: AsyncSession, record_id: str) -> Record:
    return await update_record(db, record_id, status="approved")


async def reject_record(db: AsyncSession, record_id: str) -> Record:
    return await update_record(db, record_id, status="rejected")


async def bulk_approve(db: AsyncSession, source_id: str, min_confidence: int = 70) -> int:
    result = await db.execute(
        select(Record).where(
            Record.source_id == source_id,
            Record.status == "pending",
            Record.confidence_score >= min_confidence,
        )
    )
    records = list(result.scalars().all())
    for record in records:
        record.status = "approved"
        record.updated_at = datetime.now(UTC)
    await db.commit()
    return len(records)


async def count_records(
    db: AsyncSession, source_id: str | None = None, status: str | None = None
) -> int:
    stmt = select(func.count(Record.id))
    if source_id:
        stmt = stmt.where(Record.source_id == source_id)
    if status:
        stmt = stmt.where(Record.status == status)
    result = await db.execute(stmt)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Image CRUD
# ---------------------------------------------------------------------------


async def create_image(db: AsyncSession, source_id: str, url: str, **kwargs: Any) -> Image:
    image = Image(source_id=source_id, url=url, **kwargs)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def list_images(
    db: AsyncSession,
    record_id: str | None = None,
    source_id: str | None = None,
    image_type: str | None = None,
    is_valid: bool | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Image]:
    stmt = select(Image)
    if record_id:
        stmt = stmt.where(Image.record_id == record_id)
    if source_id:
        stmt = stmt.where(Image.source_id == source_id)
    if image_type:
        stmt = stmt.where(Image.image_type == image_type)
    if is_valid is not None:
        stmt = stmt.where(Image.is_valid == is_valid)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def set_primary_image(db: AsyncSession, record_id: str, image_id: str) -> Record:
    record = await get_record(db, record_id)
    if record is None:
        raise ValueError(f"Record {record_id} not found")
    record.primary_image_id = image_id
    record.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Job CRUD
# ---------------------------------------------------------------------------


async def create_job(
    db: AsyncSession, source_id: str, job_type: str, payload: dict[str, Any]
) -> Job:
    job = Job(source_id=source_id, job_type=job_type, payload=json.dumps(payload))
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_next_pending_job(db: AsyncSession) -> Job | None:
    result = await db.execute(
        select(Job).where(Job.status == "pending").order_by(Job.created_at).limit(1)
    )
    return result.scalar_one_or_none()


async def update_job_status(
    db: AsyncSession, job_id: str, status: str, **kwargs: Any
) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise ValueError(f"Job {job_id} not found")
    job.status = status
    for key, value in kwargs.items():
        if key == "result" and isinstance(value, dict):
            value = json.dumps(value)
        setattr(job, key, value)
    await db.commit()
    await db.refresh(job)
    return job


async def list_jobs(
    db: AsyncSession, source_id: str | None = None, status: str | None = None
) -> list[Job]:
    stmt = select(Job)
    if source_id:
        stmt = stmt.where(Job.source_id == source_id)
    if status:
        stmt = stmt.where(Job.status == status)
    stmt = stmt.order_by(Job.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
