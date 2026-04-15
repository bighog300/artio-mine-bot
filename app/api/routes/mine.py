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
PIPELINE_JOB_TIMEOUT_SECONDS = 900


def _ensure_worker_runtime() -> None:
    if settings.environment in {"production", "vercel"}:
        raise HTTPException(
            status_code=503,
            detail="This task must run in a worker environment, not Vercel.",
        )


def _enqueue_pipeline_job(job_id: str, source_id: str, job_type: str, payload: dict) -> str:
    rq_job = get_default_queue().enqueue(
        "app.pipeline.runner.process_pipeline_job",
        job_id,
        source_id,
        job_type,
        payload,
        job_timeout=PIPELINE_JOB_TIMEOUT_SECONDS,
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


async def _choose_resume_job_type(db: AsyncSession, source_id: str) -> str:
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    pending_extraction = await crud.count_pages_in_statuses(
        db,
        source_id,
        statuses=["fetched", "classified"],
    )

    if pending_extraction > 0:
        chosen = "extract_page"
    elif source.status in {"paused", "error", "crawling", "mapping"} and source.site_map:
        chosen = "crawl_section"
    else:
        chosen = "run_full_pipeline"

    logger.info(
        "resume_stage_selected",
        source_id=source_id,
        source_status=source.status,
        pending_extraction=pending_extraction,
        selected_job_type=chosen,
    )
    return chosen


async def _handle_enqueue_failure(
    db: AsyncSession,
    *,
    source_id: str,
    job_id: str | None,
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
    if job_id:
        try:
            await crud.update_job_status(
                db, job_id, "failed", error_message=f"Queue enqueue failed: {exc}"
            )
        except ValueError:
            logger.warning("enqueue_failure_job_missing", job_id=job_id, source_id=source_id)
    try:
        await crud.update_source(
            db,
            source_id,
            status="error",
            error_message="Failed to enqueue mining job. Check Redis/worker availability.",
        )
    except ValueError:
        logger.warning("enqueue_failure_source_missing", source_id=source_id)


async def _create_and_enqueue_job(
    db: AsyncSession,
    *,
    source_id: str,
    job_type: str,
    payload: dict,
) -> str:
    source = await crud.wait_for_source(db, source_id, retries=3, delay_seconds=0.2)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    # Persist source+job state before enqueue so workers always see durable rows.
    await crud.update_source(db, source_id, status="queued", error_message=None)
    job = await crud.create_job(
        db,
        source_id=source_id,
        job_type=job_type,
        payload=payload,
    )
    persisted_job = await crud.wait_for_job(db, job.id, retries=3, delay_seconds=0.2)
    if persisted_job is None:
        logger.error("job_not_visible_after_commit", source_id=source_id, job_id=job.id)
        raise HTTPException(status_code=500, detail="Job persistence failed before enqueue")

    await crud.update_job_status(db, persisted_job.id, "queued")
    return _enqueue_pipeline_job(persisted_job.id, source_id, job_type, payload)


@router.post("/{source_id}/start", response_model=MineStartResponse, status_code=200)
async def start_mining(
    source_id: str,
    body: MineStartRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    _ensure_worker_runtime()
    _assert_queue_available()

    payload = body.model_dump() if body else {}
    try:
        rq_job_id = await _create_and_enqueue_job(
            db,
            source_id=source_id,
            job_type="run_full_pipeline",
            payload=payload,
        )
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await _handle_enqueue_failure(
            db,
            source_id=source_id,
            job_id=None,
            job_type="run_full_pipeline",
            exc=exc,
        )
        raise HTTPException(
            status_code=503,
            detail="Failed to start mining: queue infrastructure unavailable.",
        ) from exc

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

    try:
        rq_job_id = await _create_and_enqueue_job(
            db, source_id=source_id, job_type="map_site", payload={}
        )
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await _handle_enqueue_failure(
            db, source_id=source_id, job_id=None, job_type="map_site", exc=exc
        )
        raise HTTPException(status_code=503, detail="Failed to queue site mapping job.") from exc
    return {"job_id": rq_job_id, "source_id": source_id, "status": "queued", "site_map": None}


@router.post("/{source_id}/crawl", status_code=202)
async def crawl_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    _ensure_worker_runtime()
    _assert_queue_available()

    try:
        rq_job_id = await _create_and_enqueue_job(
            db, source_id=source_id, job_type="crawl_section", payload={}
        )
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await _handle_enqueue_failure(
            db, source_id=source_id, job_id=None, job_type="crawl_section", exc=exc
        )
        raise HTTPException(status_code=503, detail="Failed to queue crawl job.") from exc
    return {"job_id": rq_job_id, "status": "queued"}


@router.post("/{source_id}/extract", status_code=202)
async def extract_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    _ensure_worker_runtime()
    _assert_queue_available()

    try:
        rq_job_id = await _create_and_enqueue_job(
            db, source_id=source_id, job_type="extract_page", payload={}
        )
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await _handle_enqueue_failure(
            db, source_id=source_id, job_id=None, job_type="extract_page", exc=exc
        )
        raise HTTPException(status_code=503, detail="Failed to queue extraction job.") from exc
    return {"job_id": rq_job_id, "status": "queued"}


@router.post("/{source_id}/pause")
async def pause_mining(source_id: str, db: AsyncSession = Depends(get_db)):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await crud.update_source(db, source_id, status="paused", operational_status="paused", queue_paused=True)
    return {"source_id": source_id, "status": "paused"}


@router.post("/{source_id}/resume", status_code=202)
async def resume_mining(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    _ensure_worker_runtime()
    _assert_queue_available()

    resume_job_type = await _choose_resume_job_type(db, source_id)
    try:
        rq_job_id = await _create_and_enqueue_job(
            db,
            source_id=source_id,
            job_type=resume_job_type,
            payload={},
        )
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        await _handle_enqueue_failure(
            db,
            source_id=source_id,
            job_id=None,
            job_type=resume_job_type,
            exc=exc,
        )
        raise HTTPException(status_code=503, detail="Failed to resume mining job.") from exc

    return {
        "job_id": rq_job_id,
        "source_id": source_id,
        "status": "queued",
        "message": f"Mining resume queued for worker execution ({resume_job_type})",
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

    page_counts = await crud.count_pages_by_status(db, source_id=source_id)
    pages_crawled = page_counts.get("fetched", 0)
    pages_classified = page_counts.get("classified", 0)
    pages_skipped = page_counts.get("skipped", 0)
    pages_error = page_counts.get("error", 0)
    pages_eligible = page_counts.get("fetched", 0) + page_counts.get("classified", 0)

    records_extracted = await crud.count_records(db, source_id=source_id)
    record_counts = await crud.count_records_by_type(db, source_id=source_id)
    records_by_type = {
        "artist": record_counts.get("artist", 0),
        "event": record_counts.get("event", 0),
        "exhibition": record_counts.get("exhibition", 0),
        "venue": record_counts.get("venue", 0),
        "artwork": record_counts.get("artwork", 0),
    }
    images_count = await crud.count_images(db, source_id=source_id)

    total_pages = source.total_pages or 1
    percent = min(int((pages_crawled / total_pages) * 100), 100) if total_pages > 0 else 0

    progress = MineStatusProgress(
        pages_crawled=pages_crawled,
        pages_total_estimated=total_pages,
        pages_eligible_for_extraction=pages_eligible,
        pages_classified=pages_classified,
        pages_skipped=pages_skipped,
        pages_error=pages_error,
        records_extracted=records_extracted,
        records_by_type=records_by_type,
        images_collected=images_count,
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
