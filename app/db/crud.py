import json
from asyncio import sleep
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import cosine_similarity, create_embedding
from app.db.models import AuditAction, DuplicateReview, EntityRelationship, Image, Job, Page, Record, Source

logger = structlog.get_logger()


def _extract_completeness_and_conflicts(raw_data: str | None) -> tuple[int, bool]:
    if not raw_data:
        return 0, False
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError:
        return 0, False
    completeness = payload.get("completeness_score", 0)
    has_conflicts = bool(payload.get("conflicts", {}))
    return int(completeness or 0), has_conflicts


def _record_text_for_embedding(record_type: str, values: dict[str, Any]) -> str:
    segments: list[str] = []
    if record_type == "artist":
        for key in ("title", "bio", "nationality", "city", "country", "description"):
            value = values.get(key)
            if value:
                segments.append(str(value))
        for key in ("mediums", "collections"):
            value = values.get(key)
            if isinstance(value, list):
                segments.extend(str(item) for item in value)
    elif record_type == "exhibition":
        for key in ("title", "description", "venue_name", "venue_address", "city", "country"):
            value = values.get(key)
            if value:
                segments.append(str(value))
    elif record_type in {"artist_article", "article"}:
        for key in ("title", "description", "source_url"):
            value = values.get(key)
            if value:
                segments.append(str(value))
    return " ".join(segments)


def _build_embedding_payload(record_type: str, values: dict[str, Any]) -> str | None:
    text = _record_text_for_embedding(record_type, values)
    if not text.strip():
        return None
    return json.dumps(create_embedding(text))


def _ordered_pair(left_record_id: str, right_record_id: str) -> tuple[str, str]:
    return (left_record_id, right_record_id) if left_record_id <= right_record_id else (right_record_id, left_record_id)

# ---------------------------------------------------------------------------
# Source CRUD
# ---------------------------------------------------------------------------


async def create_source(
    db: AsyncSession,
    url: str,
    name: str | None = None,
    crawl_hints: str | None = None,
) -> Source:
    source = Source(url=url, name=name, crawl_hints=crawl_hints)
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


async def wait_for_source(
    db: AsyncSession,
    source_id: str,
    *,
    retries: int = 3,
    delay_seconds: float = 0.2,
) -> Source | None:
    """Wait briefly for source visibility across transactions/processes."""
    for attempt in range(retries):
        source = await get_source(db, source_id)
        if source is not None:
            return source
        if attempt < retries - 1:
            await sleep(delay_seconds)
    return None


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
    kwargs.setdefault("status", "fetched")
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


async def list_pages_by_statuses(
    db: AsyncSession,
    source_id: str,
    statuses: list[str],
    *,
    limit: int = 10000,
) -> list[Page]:
    stmt: Select[tuple[Page]] = (
        select(Page)
        .where(Page.source_id == source_id, Page.status.in_(statuses))
        .limit(limit)
    )
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


async def count_pages_in_statuses(db: AsyncSession, source_id: str, statuses: list[str]) -> int:
    stmt = select(func.count(Page.id)).where(Page.source_id == source_id, Page.status.in_(statuses))
    result = await db.execute(stmt)
    return result.scalar_one()


async def count_pages_by_status(db: AsyncSession, source_id: str) -> dict[str, int]:
    stmt = (
        select(Page.status, func.count(Page.id))
        .where(Page.source_id == source_id)
        .group_by(Page.status)
    )
    result = await db.execute(stmt)
    return {status: count for status, count in result.all()}


# ---------------------------------------------------------------------------
# Record CRUD
# ---------------------------------------------------------------------------


async def create_record(
    db: AsyncSession, source_id: str, record_type: str, **kwargs: Any
) -> Record:
    embedding_payload = _build_embedding_payload(record_type, kwargs)
    if embedding_payload is not None:
        kwargs["embedding_vector"] = embedding_payload
        kwargs["embedding_updated_at"] = datetime.now(UTC)
    # Serialize list fields to JSON strings
    for field in ("artist_names", "mediums", "collections", "confidence_reasons"):
        if field in kwargs and isinstance(kwargs[field], list):
            kwargs[field] = json.dumps(kwargs[field])
    if "raw_data" in kwargs:
        completeness, has_conflicts = _extract_completeness_and_conflicts(kwargs.get("raw_data"))
        kwargs.setdefault("completeness_score", completeness)
        kwargs.setdefault("has_conflicts", has_conflicts)
    record = Record(source_id=source_id, record_type=record_type, **kwargs)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_record_by_page_and_type(
    db: AsyncSession,
    *,
    source_id: str,
    page_id: str,
    record_type: str,
) -> Record | None:
    result = await db.execute(
        select(Record).where(
            Record.source_id == source_id,
            Record.page_id == page_id,
            Record.record_type == record_type,
        )
    )
    return result.scalar_one_or_none()


async def get_artist_record_by_family_key(
    db: AsyncSession,
    *,
    source_id: str,
    family_key: str,
) -> Record | None:
    result = await db.execute(
        select(Record).where(
            Record.source_id == source_id,
            Record.record_type == "artist",
            Record.raw_data.is_not(None),
            Record.raw_data.contains(f'"artist_family_key": "{family_key}"'),
        )
    )
    return result.scalars().first()


async def get_record_by_item_fingerprint(
    db: AsyncSession,
    *,
    source_id: str,
    page_id: str | None,
    record_type: str,
    item_fingerprint: str,
) -> Record | None:
    stmt = select(Record).where(
        Record.source_id == source_id,
        Record.record_type == record_type,
        Record.raw_data.is_not(None),
        Record.raw_data.contains(f'"item_fingerprint": "{item_fingerprint}"'),
    )
    if page_id is not None:
        stmt = stmt.where(Record.page_id == page_id)
    result = await db.execute(stmt)
    return result.scalars().first()


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


async def search_records(
    db: AsyncSession,
    *,
    record_type: str,
    query: str | None = None,
    location: str | None = None,
    min_completeness_score: int | None = None,
    has_exhibitions: bool | None = None,
    has_articles: bool | None = None,
    has_conflicts: bool | None = None,
    sort_by: str = "completeness",
    skip: int = 0,
    limit: int = 50,
) -> list[Record]:
    stmt = select(Record).where(Record.record_type == record_type)
    if query:
        query_filter = f"%{query}%"
        stmt = stmt.where(
            or_(
                Record.title.ilike(query_filter),
                Record.description.ilike(query_filter),
                Record.bio.ilike(query_filter),
            )
        )
    if location:
        location_filter = f"%{location}%"
        stmt = stmt.where(
            or_(
                Record.city.ilike(location_filter),
                Record.country.ilike(location_filter),
                Record.venue_name.ilike(location_filter),
                Record.venue_address.ilike(location_filter),
                Record.nationality.ilike(location_filter),
            )
        )
    if min_completeness_score is not None:
        stmt = stmt.where(Record.completeness_score >= min_completeness_score)
    if has_conflicts is not None:
        stmt = stmt.where(Record.has_conflicts.is_(has_conflicts))
    if has_exhibitions is not None:
        comparator = Record.raw_data.contains('"exhibitions"')
        stmt = stmt.where(comparator if has_exhibitions else ~comparator)
    if has_articles is not None:
        comparator = Record.raw_data.contains('"articles"')
        stmt = stmt.where(comparator if has_articles else ~comparator)

    if sort_by == "alphabetical":
        stmt = stmt.order_by(Record.title.asc().nullslast())
    elif sort_by == "number_of_exhibitions":
        stmt = stmt.order_by(Record.raw_data.desc().nullslast())
    else:
        stmt = stmt.order_by(Record.completeness_score.desc(), Record.title.asc().nullslast())

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_search_records(
    db: AsyncSession,
    *,
    record_type: str,
    query: str | None = None,
    location: str | None = None,
    min_completeness_score: int | None = None,
    has_exhibitions: bool | None = None,
    has_articles: bool | None = None,
    has_conflicts: bool | None = None,
) -> int:
    stmt = select(func.count(Record.id)).where(Record.record_type == record_type)
    if query:
        query_filter = f"%{query}%"
        stmt = stmt.where(
            or_(
                Record.title.ilike(query_filter),
                Record.description.ilike(query_filter),
                Record.bio.ilike(query_filter),
            )
        )
    if location:
        location_filter = f"%{location}%"
        stmt = stmt.where(
            or_(
                Record.city.ilike(location_filter),
                Record.country.ilike(location_filter),
                Record.venue_name.ilike(location_filter),
                Record.venue_address.ilike(location_filter),
                Record.nationality.ilike(location_filter),
            )
        )
    if min_completeness_score is not None:
        stmt = stmt.where(Record.completeness_score >= min_completeness_score)
    if has_conflicts is not None:
        stmt = stmt.where(Record.has_conflicts.is_(has_conflicts))
    if has_exhibitions is not None:
        comparator = Record.raw_data.contains('"exhibitions"')
        stmt = stmt.where(comparator if has_exhibitions else ~comparator)
    if has_articles is not None:
        comparator = Record.raw_data.contains('"articles"')
        stmt = stmt.where(comparator if has_articles else ~comparator)
    result = await db.execute(stmt)
    return result.scalar_one()


async def update_record(db: AsyncSession, record_id: str, **kwargs: Any) -> Record:
    record = await get_record(db, record_id)
    if record is None:
        raise ValueError(f"Record {record_id} not found")
    updated_values: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key in ("artist_names", "mediums", "collections", "confidence_reasons") and isinstance(
            value, list
        ):
            value = json.dumps(value)
        setattr(record, key, value)
        updated_values[key] = value
    embedding_payload = _build_embedding_payload(record.record_type, {**record.__dict__, **updated_values})
    if embedding_payload is not None:
        record.embedding_vector = embedding_payload
        record.embedding_updated_at = datetime.now(UTC)
    if "raw_data" in kwargs:
        completeness, has_conflicts = _extract_completeness_and_conflicts(record.raw_data)
        record.completeness_score = completeness
        record.has_conflicts = has_conflicts
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
    db: AsyncSession,
    source_id: str | None = None,
    status: str | None = None,
    record_type: str | None = None,
) -> int:
    stmt = select(func.count(Record.id))
    if source_id:
        stmt = stmt.where(Record.source_id == source_id)
    if status:
        stmt = stmt.where(Record.status == status)
    if record_type:
        stmt = stmt.where(Record.record_type == record_type)
    result = await db.execute(stmt)
    return result.scalar_one()


async def count_records_by_type(db: AsyncSession, source_id: str) -> dict[str, int]:
    stmt = (
        select(Record.record_type, func.count(Record.id))
        .where(Record.source_id == source_id)
        .group_by(Record.record_type)
    )
    result = await db.execute(stmt)
    return {record_type: count for record_type, count in result.all()}


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


async def count_images(db: AsyncSession, source_id: str | None = None, record_id: str | None = None) -> int:
    stmt = select(func.count(Image.id))
    if source_id:
        stmt = stmt.where(Image.source_id == source_id)
    if record_id:
        stmt = stmt.where(Image.record_id == record_id)
    result = await db.execute(stmt)
    return result.scalar_one()


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


async def get_job(db: AsyncSession, job_id: str) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def wait_for_job(
    db: AsyncSession,
    job_id: str,
    *,
    retries: int = 3,
    delay_seconds: float = 0.2,
) -> Job | None:
    """Wait briefly for job visibility across transactions/processes."""
    for attempt in range(retries):
        job = await get_job(db, job_id)
        if job is not None:
            return job
        if attempt < retries - 1:
            await sleep(delay_seconds)
    return None


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


async def list_pages_for_artist_family(
    db: AsyncSession,
    *,
    source_id: str,
    family_key: str,
) -> list[Page]:
    _, slug = family_key.split("::", 1)
    stmt = select(Page).where(
        Page.source_id == source_id,
        Page.url.contains(f"/{slug}"),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_artist_records(
    db: AsyncSession,
    *,
    source_id: str | None = None,
    limit: int = 1000,
) -> list[Record]:
    stmt = select(Record).where(Record.record_type == "artist").limit(limit)
    if source_id:
        stmt = stmt.where(Record.source_id == source_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_records_for_artist_family(
    db: AsyncSession,
    *,
    source_id: str,
    page_ids: list[str],
) -> list[Record]:
    if not page_ids:
        return []
    stmt = select(Record).where(
        Record.source_id == source_id,
        Record.page_id.in_(page_ids),
        Record.record_type.in_(["exhibition", "artist_article", "artist_press", "artist_memory"]),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def parse_embedding(embedding_value: str | None) -> list[float]:
    if not embedding_value:
        return []
    try:
        parsed = json.loads(embedding_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [float(item) for item in parsed]


def embedding_similarity(left: Record, right: Record) -> float:
    return cosine_similarity(parse_embedding(left.embedding_vector), parse_embedding(right.embedding_vector))


async def upsert_entity_relationship(
    db: AsyncSession,
    *,
    source_id: str,
    from_record_id: str,
    to_record_id: str,
    relationship_type: str,
    metadata: dict[str, Any] | None = None,
) -> EntityRelationship:
    stmt = select(EntityRelationship).where(
        EntityRelationship.source_id == source_id,
        EntityRelationship.from_record_id == from_record_id,
        EntityRelationship.to_record_id == to_record_id,
        EntityRelationship.relationship_type == relationship_type,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        if metadata is not None:
            existing.metadata_json = json.dumps(metadata)
        await db.commit()
        await db.refresh(existing)
        return existing

    rel = EntityRelationship(
        source_id=source_id,
        from_record_id=from_record_id,
        to_record_id=to_record_id,
        relationship_type=relationship_type,
        metadata_json=json.dumps(metadata) if metadata is not None else None,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


async def list_relationships_for_record(
    db: AsyncSession,
    *,
    source_id: str,
    record_id: str,
) -> list[EntityRelationship]:
    stmt = select(EntityRelationship).where(
        EntityRelationship.source_id == source_id,
        or_(
            EntityRelationship.from_record_id == record_id,
            EntityRelationship.to_record_id == record_id,
        ),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def upsert_duplicate_review(
    db: AsyncSession,
    *,
    left_record_id: str,
    right_record_id: str,
    similarity_score: int,
    reason: str,
) -> DuplicateReview:
    left_id, right_id = _ordered_pair(left_record_id, right_record_id)
    stmt = select(DuplicateReview).where(
        DuplicateReview.left_record_id == left_id,
        DuplicateReview.right_record_id == right_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        existing.similarity_score = similarity_score
        existing.reason = reason
        await db.commit()
        await db.refresh(existing)
        return existing

    review = DuplicateReview(
        left_record_id=left_id,
        right_record_id=right_id,
        similarity_score=similarity_score,
        reason=reason,
        status="pending",
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def list_duplicate_reviews(
    db: AsyncSession,
    *,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[DuplicateReview]:
    stmt = select(DuplicateReview).order_by(DuplicateReview.similarity_score.desc(), DuplicateReview.created_at.desc())
    if status:
        stmt = stmt.where(DuplicateReview.status == status)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_duplicate_reviews(db: AsyncSession, *, status: str | None = None) -> int:
    stmt = select(func.count(DuplicateReview.id))
    if status:
        stmt = stmt.where(DuplicateReview.status == status)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_duplicate_review_by_pair(
    db: AsyncSession,
    *,
    left_record_id: str,
    right_record_id: str,
) -> DuplicateReview | None:
    left_id, right_id = _ordered_pair(left_record_id, right_record_id)
    stmt = select(DuplicateReview).where(
        DuplicateReview.left_record_id == left_id,
        DuplicateReview.right_record_id == right_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def set_duplicate_review_status(
    db: AsyncSession,
    *,
    review_id: str,
    status: str,
    reviewed_by: str | None = None,
    merge_target_id: str | None = None,
) -> DuplicateReview:
    stmt = select(DuplicateReview).where(DuplicateReview.id == review_id)
    review = (await db.execute(stmt)).scalar_one_or_none()
    if review is None:
        raise ValueError(f"Duplicate review {review_id} not found")
    review.status = status
    review.reviewed_by = reviewed_by
    review.reviewed_at = datetime.now(UTC)
    review.merge_target_id = merge_target_id
    await db.commit()
    await db.refresh(review)
    return review


async def create_audit_action(
    db: AsyncSession,
    *,
    action_type: str,
    user_id: str | None = None,
    source_id: str | None = None,
    record_id: str | None = None,
    affected_record_ids: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> AuditAction:
    action = AuditAction(
        action_type=action_type,
        user_id=user_id,
        source_id=source_id,
        record_id=record_id,
        affected_record_ids=json.dumps(affected_record_ids or []),
        details_json=json.dumps(details) if details is not None else None,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


async def list_audit_actions(
    db: AsyncSession,
    *,
    action_type: str | None = None,
    source_id: str | None = None,
    record_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AuditAction]:
    stmt = select(AuditAction).order_by(AuditAction.created_at.desc())
    if action_type:
        stmt = stmt.where(AuditAction.action_type == action_type)
    if source_id:
        stmt = stmt.where(AuditAction.source_id == source_id)
    if record_id:
        stmt = stmt.where(AuditAction.record_id == record_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_audit_actions(db: AsyncSession, *, action_type: str | None = None) -> int:
    stmt = select(func.count(AuditAction.id))
    if action_type:
        stmt = stmt.where(AuditAction.action_type == action_type)
    result = await db.execute(stmt)
    return result.scalar_one()
