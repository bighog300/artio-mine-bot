from fastapi import APIRouter, Depends, HTTPException
import json
import structlog
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import (
    SourceActionResponse,
    SourceCreate,
    SourceDetailResponse,
    SourceResponse,
    SourceStats,
    SourceUpdate,
)
from app.db import crud

router = APIRouter(prefix="/sources", tags=["sources"])
logger = structlog.get_logger()
SOURCE_OPERATIONAL_STATUSES = {"idle", "running", "paused", "stopping", "failed", "completed"}


@router.get("", response_model=dict)
async def list_sources(
    skip: int = 0,
    limit: int = 50,
    enabled: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    try:
        sources = await crud.list_sources(db, skip=skip, limit=limit, enabled=enabled)
        total = len(sources)  # Simple count for now

        items = []
        for source in sources:
            stats_data = await crud.get_source_stats(db, source.id)
            source_dict = SourceResponse.model_validate(source).model_dump()
            source_dict["stats"] = SourceStats(**stats_data).model_dump()
            items.append(source_dict)

        return {"items": items, "total": total, "skip": skip, "limit": limit}
    except SQLAlchemyError as exc:
        logger.error(
            "sources_list_db_error",
            skip=skip,
            limit=limit,
            enabled=enabled,
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail="Database error while listing sources. Check API logs for details.",
        ) from exc


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(
    body: SourceCreate,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    existing = await crud.get_source_by_url(db, body.url)
    if existing:
        raise HTTPException(status_code=409, detail="Source with this URL already exists")

    try:
        source = await crud.create_source(
            db,
            url=body.url,
            name=body.name,
            crawl_intent=body.crawl_intent,
            crawl_hints=json.dumps(body.crawl_hints) if body.crawl_hints is not None else None,
            extraction_rules=json.dumps(body.extraction_rules) if body.extraction_rules is not None else None,
            max_depth=body.max_depth,
            max_pages=body.max_pages,
            enabled=body.enabled,
        )
        return source
    except IntegrityError as exc:
        await db.rollback()
        logger.warning(
            "source_create_integrity_error",
            url=body.url,
            error=str(exc),
        )
        raise HTTPException(status_code=409, detail="Source with this URL already exists") from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error(
            "source_create_db_error",
            url=body.url,
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail="Database error while creating source. Check API logs for details.",
        ) from exc


@router.get("/{source_id}", response_model=SourceDetailResponse)
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: str,
    body: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if "crawl_hints" in kwargs:
        kwargs["crawl_hints"] = json.dumps(kwargs["crawl_hints"])
    if "extraction_rules" in kwargs:
        kwargs["extraction_rules"] = json.dumps(kwargs["extraction_rules"])
    if "status" in kwargs and kwargs["status"] not in SOURCE_OPERATIONAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid source status '{kwargs['status']}'")
    if "operational_status" in kwargs and kwargs["operational_status"] not in SOURCE_OPERATIONAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid source status '{kwargs['operational_status']}'")
    if kwargs:
        source = await crud.update_source(db, source_id, **kwargs)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await crud.delete_source(db, source_id)


@router.get("/{source_id}/jobs")
async def list_source_jobs(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    jobs = await crud.list_jobs(db, source_id=source_id)
    return {
        "items": [
            {
                "id": job.id,
                "source_id": job.source_id,
                "job_type": job.job_type,
                "status": job.status,
                "attempts": job.attempts,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message,
            }
            for job in jobs
        ]
    }


async def _ensure_source(db: AsyncSession, source_id: str):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/{source_id}/actions/start-discovery", response_model=SourceActionResponse)
async def start_discovery_action(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    await _ensure_source(db, source_id)
    job = await crud.create_job(db, source_id=source_id, job_type="map_site", payload={})
    source = await crud.set_source_operational_status(db, source_id, "running", queue_paused=False, error_message=None)
    return SourceActionResponse(source_id=source.id, status=source.status, operational_status=source.operational_status, queued_jobs=1 if job else 0)


@router.post("/{source_id}/actions/start-full-mining", response_model=SourceActionResponse)
async def start_full_mining_action(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    await _ensure_source(db, source_id)
    job = await crud.create_job(db, source_id=source_id, job_type="run_full_pipeline", payload={})
    source = await crud.set_source_operational_status(db, source_id, "running", queue_paused=False, error_message=None)
    return SourceActionResponse(source_id=source.id, status=source.status, operational_status=source.operational_status, queued_jobs=1 if job else 0)


@router.post("/{source_id}/actions/pause", response_model=SourceActionResponse)
async def pause_source_action(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await _ensure_source(db, source_id)
    source = await crud.set_source_operational_status(db, source_id, "paused", queue_paused=True)
    return SourceActionResponse(source_id=source.id, status=source.status, operational_status=source.operational_status)


@router.post("/{source_id}/actions/resume", response_model=SourceActionResponse)
async def resume_source_action(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    await _ensure_source(db, source_id)
    source = await crud.set_source_operational_status(db, source_id, "running", queue_paused=False, error_message=None)
    return SourceActionResponse(source_id=source.id, status=source.status, operational_status=source.operational_status)


@router.post("/{source_id}/actions/stop", response_model=SourceActionResponse)
async def stop_source_action(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    await _ensure_source(db, source_id)
    source = await crud.set_source_operational_status(db, source_id, "stopping", queue_paused=True)
    cancelled_jobs = await crud.cancel_non_terminal_jobs_for_source(db, source_id)
    source = await crud.set_source_operational_status(db, source_id, "idle", queue_paused=False)
    return SourceActionResponse(source_id=source.id, status=source.status, operational_status=source.operational_status, queued_jobs=cancelled_jobs)


@router.post("/{source_id}/actions/retry-failed", response_model=SourceActionResponse)
async def retry_failed_source_action(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    await _ensure_source(db, source_id)
    retried_jobs = await crud.retry_failed_jobs_for_source(db, source_id)
    status = "running" if retried_jobs > 0 else "idle"
    source = await crud.set_source_operational_status(db, source_id, status, queue_paused=False)
    return SourceActionResponse(source_id=source.id, status=source.status, operational_status=source.operational_status, queued_jobs=retried_jobs)
