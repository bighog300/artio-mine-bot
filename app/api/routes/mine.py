from fastapi import APIRouter, Depends, HTTPException
import structlog
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import (
    JobSummary,
    MineStartRequest,
    MineStartResponse,
    MineStatusProgress,
    MineStatusResponse,
)
from app.config import settings
from app.db import crud
from app.queue import QueueUnavailableError, check_queue_health, get_default_queue

router = APIRouter(prefix="/mine", tags=["mining"])
logger = structlog.get_logger()


def _ensure_worker_runtime() -> None:
    if settings.environment in {"production", "vercel"}:
        raise HTTPException(
            status_code=503,
            detail="This task must run in a worker environment, not Vercel.",
        )


def _enqueue_pipeline_job(job_id: str, source_id: str, job_type: str, payload: dict) -> str:
    rq_job = get_default_queue().enqueue(
        "app.pipeline.runner.process_pipeline_job",
        job_id=job_id,
        source_id=source_id,
        job_type=job_type,
        payload=payload,
    )
    return rq_job.id


def _assert_queue_available(require_worker: bool = True) -> None:
    health = check_queue_health()
    if not health.redis_ok:
        raise HTTPException(
            status_code=503,
            detail="Queue unavailable: cannot reach Redis. Check queue infrastructure.",
        )
    if require_worker and not health.workers_available:
        raise HTTPException(
            status_code=503,
            detail="Queue unavailable: no active workers are connected.",
        )


async def _handle_enqueue_failure(
    db: AsyncSession,
    *,
    source_id: str,
    job_id: str,
    job_type: str,
    exc: Exception,
) -> None:
    logger.error(
        "queue_enqueue_failed",
        source_id=source_id,
        job_id=job_id,
        job_type=job_type,
        error=str(exc),
    )
    await crud.update_job_status(db, job_id, "failed", error_message=f"Queue enqueue failed: {exc}")
    await crud.update_source(
        db,
        source_id,
        status="error",
        error_message="Failed to enqueue mining job. Check Redis/worker availability.",
    )


@router.post("/{source_id}/start", response_model=MineStartResponse, status_code=200)
async def start_mining(
    source_id: str,
    body: MineStartRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    _ensure_worker_runtime()
    _assert_queue_available()

    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job = await crud.create_job(
        db,
        source_id=source_id,
        job_type="run_full_pipeline",
        payload=body.model_dump() if body else {},
    )
    payload = body.model_dump() if body else {}
    try:
        rq_job_id = _enqueue_pipeline_job(job.id, source_id, "run_full_pipeline", payload)
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await _handle_enqueue_failure(
            db,
            source_id=source_id,
            job_id=job.id,
            job_type="run_full_pipeline",
            exc=exc,
        )
        raise HTTPException(
            status_code=503,
            detail="Failed to start mining: queue infrastructure unavailable.",
        ) from exc
    await crud.update_source(db, source_id, status="queued", error_message=None)
    await crud.update_job_status(db, job.id, "queued")

    return MineStartResponse(
        job_id=rq_job_id,
        source_id=source_id,
        status="queued",
        message="Mining job queued for worker execution",
    )


@router.post("/{source_id}/map", status_code=202)
async def map_site(source_id: str, db: AsyncSession = Depends(get_db)):
    _ensure_worker_runtime()
    _assert_queue_available()

    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job = await crud.create_job(
        db,
        source_id=source_id,
        job_type="map_site",
        payload={},
    )
    try:
        rq_job_id = _enqueue_pipeline_job(job.id, source_id, "map_site", {})
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await _handle_enqueue_failure(
            db, source_id=source_id, job_id=job.id, job_type="map_site", exc=exc
        )
        raise HTTPException(status_code=503, detail="Failed to queue site mapping job.") from exc
    await crud.update_source(db, source_id, status="queued", error_message=None)
    await crud.update_job_status(db, job.id, "queued")
    return {"job_id": rq_job_id, "source_id": source_id, "status": "queued", "site_map": None}


@router.post("/{source_id}/crawl", status_code=202)
async def crawl_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    _ensure_worker_runtime()
    _assert_queue_available()

    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job = await crud.create_job(
        db, source_id=source_id, job_type="crawl_section", payload={}
    )
    try:
        rq_job_id = _enqueue_pipeline_job(job.id, source_id, "crawl_section", {})
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await _handle_enqueue_failure(
            db, source_id=source_id, job_id=job.id, job_type="crawl_section", exc=exc
        )
        raise HTTPException(status_code=503, detail="Failed to queue crawl job.") from exc
    await crud.update_source(db, source_id, status="queued", error_message=None)
    await crud.update_job_status(db, job.id, "queued")
    return {"job_id": rq_job_id, "status": "queued"}


@router.post("/{source_id}/extract", status_code=202)
async def extract_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    _ensure_worker_runtime()
    _assert_queue_available()

    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job = await crud.create_job(
        db, source_id=source_id, job_type="extract_page", payload={}
    )
    try:
        rq_job_id = _enqueue_pipeline_job(job.id, source_id, "extract_page", {})
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await _handle_enqueue_failure(
            db, source_id=source_id, job_id=job.id, job_type="extract_page", exc=exc
        )
        raise HTTPException(status_code=503, detail="Failed to queue extraction job.") from exc
    await crud.update_source(db, source_id, status="queued", error_message=None)
    await crud.update_job_status(db, job.id, "queued")
    return {"job_id": rq_job_id, "status": "queued"}


@router.post("/{source_id}/pause")
async def pause_mining(source_id: str, db: AsyncSession = Depends(get_db)):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await crud.update_source(db, source_id, status="paused")
    return {"source_id": source_id, "status": "paused"}


@router.post("/{source_id}/resume", status_code=202)
async def resume_mining(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    _ensure_worker_runtime()
    _assert_queue_available()

    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job = await crud.create_job(
        db,
        source_id=source_id,
        job_type="run_full_pipeline",
        payload={},
    )
    try:
        rq_job_id = _enqueue_pipeline_job(job.id, source_id, "run_full_pipeline", {})
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await _handle_enqueue_failure(
            db,
            source_id=source_id,
            job_id=job.id,
            job_type="run_full_pipeline",
            exc=exc,
        )
        raise HTTPException(status_code=503, detail="Failed to resume mining job.") from exc
    await crud.update_source(db, source_id, status="queued", error_message=None)
    await crud.update_job_status(db, job.id, "queued")

    return {
        "job_id": rq_job_id,
        "source_id": source_id,
        "status": "queued",
        "message": "Mining resume queued for worker execution",
    }


@router.get("/{source_id}/status", response_model=MineStatusResponse)
async def get_mining_status(source_id: str, db: AsyncSession = Depends(get_db)):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    jobs = await crud.list_jobs(db, source_id=source_id)
    current_job = None
    for job in jobs:
        if job.status in {"queued", "pending", "running"}:
            current_job = JobSummary.model_validate(job)
            break

    pages_crawled = await crud.count_pages(db, source_id=source_id, status="fetched")
    records_extracted = await crud.count_records(db, source_id=source_id)
    total_pages = source.total_pages or 1
    percent = min(int((pages_crawled / total_pages) * 100), 100) if total_pages > 0 else 0

    progress = MineStatusProgress(
        pages_crawled=pages_crawled,
        pages_total_estimated=total_pages,
        records_extracted=records_extracted,
        percent_complete=percent,
    )

    return MineStatusResponse(
        source_id=source_id,
        status=source.status,
        current_job=current_job,
        progress=progress,
    )


@router.get("/queue/health", status_code=200)
async def queue_health():
    health = check_queue_health()
    return {
        "redis_ok": health.redis_ok,
        "workers_available": health.workers_available,
        "worker_count": health.worker_count,
    }
