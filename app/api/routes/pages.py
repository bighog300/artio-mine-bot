from fastapi import APIRouter, Depends, HTTPException
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import require_worker_environment
from app.db import crud
from app.queue import QueueUnavailableError, get_default_queue

router = APIRouter(prefix="/pages", tags=["pages"])


def _ensure_worker_runtime() -> None:
    try:
        require_worker_environment()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _enqueue_page_job(job_id: str, source_id: str, job_type: str, payload: dict) -> str:
    rq_job = get_default_queue().enqueue(
        "app.pipeline.runner.process_pipeline_job",
        job_id,
        source_id,
        job_type,
        payload,
        job_timeout=900,
    )
    return rq_job.id


def _page_to_dict(page, record_count: int = 0) -> dict:
    return {
        "id": page.id,
        "source_id": page.source_id,
        "url": page.url,
        "page_type": page.page_type,
        "status": page.status,
        "title": page.title,
        "depth": page.depth,
        "fetch_method": page.fetch_method,
        "crawled_at": page.crawled_at,
        "record_count": record_count,
    }


@router.get("")
async def list_pages(
    source_id: str | None = None,
    status: str | None = None,
    page_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    pages = await crud.list_pages(
        db, source_id=source_id, status=status, page_type=page_type, skip=skip, limit=limit
    )
    items = [_page_to_dict(p) for p in pages]
    return {"items": items, "total": len(items), "skip": skip, "limit": limit}


@router.get("/{page_id}")
async def get_page(page_id: str, db: AsyncSession = Depends(get_db)):
    page = await crud.get_page(db, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return {
        **_page_to_dict(page),
        "html": page.html,
        "original_url": page.original_url,
        "error_message": page.error_message,
        "created_at": page.created_at,
        "extracted_at": page.extracted_at,
    }


@router.post("/{page_id}/reclassify", status_code=202)
async def reclassify_page(page_id: str, db: AsyncSession = Depends(get_db)):
    _ensure_worker_runtime()

    page = await crud.get_page(db, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if not page.html:
        raise HTTPException(status_code=400, detail="Page has no HTML to classify")

    job = await crud.create_job(
        db,
        source_id=page.source_id,
        job_type="reclassify_page",
        payload={"page_id": page_id},
    )
    try:
        await crud.update_job_status(db, job.id, "queued")
        rq_job_id = _enqueue_page_job(job.id, page.source_id, "reclassify_page", {"page_id": page_id})
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await crud.update_job_status(
            db,
            job.id,
            "failed",
            error_message=f"Queue enqueue failed: {exc}",
        )
        raise HTTPException(status_code=503, detail="Failed to enqueue page reclassification job.") from exc
    return {"job_id": job.id, "rq_job_id": rq_job_id, "status": "queued", "page_id": page_id}


@router.post("/{page_id}/reextract", status_code=202)
async def reextract_page(page_id: str, db: AsyncSession = Depends(get_db)):
    _ensure_worker_runtime()

    page = await crud.get_page(db, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if not page.html:
        raise HTTPException(status_code=400, detail="Page has no HTML to extract")

    job = await crud.create_job(
        db,
        source_id=page.source_id,
        job_type="reextract_page",
        payload={"page_id": page_id},
    )
    try:
        await crud.update_job_status(db, job.id, "queued")
        rq_job_id = _enqueue_page_job(job.id, page.source_id, "reextract_page", {"page_id": page_id})
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await crud.update_job_status(
            db,
            job.id,
            "failed",
            error_message=f"Queue enqueue failed: {exc}",
        )
        raise HTTPException(status_code=503, detail="Failed to enqueue page re-extraction job.") from exc
    return {"job_id": job.id, "rq_job_id": rq_job_id, "status": "queued", "page_id": page_id}
