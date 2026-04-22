from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException
import json
import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.ai.client import OpenAIClient
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
from app.db.models import JobEvent, Record
from app.queue import get_default_queue

router = APIRouter(prefix="/sources", tags=["sources"])
logger = structlog.get_logger()
SOURCE_OPERATIONAL_STATUSES = {"idle", "running", "paused", "stopping", "failed", "completed"}


def _parse_json(value: str | None, default: object) -> object:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _serialize_job_run(job: object) -> dict[str, object]:
    duration_seconds: int | None = None
    started_at = getattr(job, "started_at", None)
    completed_at = getattr(job, "completed_at", None)
    if started_at is not None:
        end = completed_at or datetime.now(UTC)
        duration_seconds = max(0, int((end - started_at).total_seconds()))

    metrics = _parse_json(getattr(job, "metrics_json", None), {})
    result = _parse_json(getattr(job, "result", None), {})

    return {
        "id": getattr(job, "id"),
        "source_id": getattr(job, "source_id"),
        "job_type": getattr(job, "job_type"),
        "status": getattr(job, "status"),
        "worker_id": getattr(job, "worker_id", None),
        "attempts": getattr(job, "attempts"),
        "max_attempts": getattr(job, "max_attempts"),
        "error_message": getattr(job, "error_message"),
        "current_stage": getattr(job, "current_stage", None),
        "current_item": getattr(job, "current_item", None),
        "progress_current": getattr(job, "progress_current", 0),
        "progress_total": getattr(job, "progress_total", 0),
        "progress_percent": (
            int((getattr(job, "progress_current", 0) / getattr(job, "progress_total", 0)) * 100)
            if getattr(job, "progress_total", 0)
            else None
        ),
        "last_heartbeat_at": getattr(job, "last_heartbeat_at", None),
        "last_log_message": getattr(job, "last_log_message", None),
        "runtime_mode": result.get("runtime_mode") or metrics.get("runtime_mode"),
        "runtime_map_source": result.get("runtime_map_source") or metrics.get("runtime_map_source"),
        "deterministic_hits": int(result.get("deterministic_hits", metrics.get("deterministic_hits", 0))),
        "deterministic_misses": int(result.get("deterministic_misses", metrics.get("deterministic_misses", 0))),
        "records_created": int(result.get("records_created", metrics.get("records_created", 0))),
        "records_updated": int(result.get("records_updated", metrics.get("records_updated", 0))),
        "media_assets_captured": int(result.get("media_assets_captured", metrics.get("media_assets_captured", 0))),
        "entity_links_created": int(result.get("entity_links_created", metrics.get("entity_links_created", 0))),
        "metrics": metrics,
        "payload": _parse_json(getattr(job, "payload", None), {}),
        "result": result,
        "started_at": started_at,
        "completed_at": completed_at,
        "created_at": getattr(job, "created_at"),
        "duration_seconds": duration_seconds,
    }


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


@router.post("/{source_id}/analyze-structure", response_model=dict)
async def analyze_source_structure(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    """Analyze source site structure once and cache the mining map on the source."""
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.structure_map and source.structure_status == "analyzed":
        return {"source_id": source_id, "status": "cached", "structure": json.loads(source.structure_map)}

    await crud.update_source(db, source_id, structure_status="analyzing", structure_error=None)

    try:
        from app.crawler.fetcher import fetch
        from app.crawler.site_structure_analyzer import analyze_structure

        fetch_result = await fetch(source.url)
        if fetch_result.error or not fetch_result.html:
            raise ValueError(fetch_result.error or "Could not fetch homepage HTML")

        ai_client = OpenAIClient()
        structure = await analyze_structure(source.url, fetch_result.html, ai_client)

        await crud.update_source(
            db,
            source_id,
            structure_map=json.dumps(structure),
            structure_status="analyzed",
            structure_error=None,
            analyzed_at=datetime.now(UTC),
        )
        return {"source_id": source_id, "status": "analyzed", "structure": structure}
    except Exception as exc:
        logger.error("source_structure_analysis_failed", source_id=source_id, error=str(exc))
        await crud.update_source(
            db,
            source_id,
            structure_status="failed",
            structure_error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
        "items": [_serialize_job_run(job) for job in jobs]
    }


@router.get("/{source_id}/runtime-map", response_model=dict)
async def get_source_runtime_map(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    runtime_map, runtime_map_source = await crud.get_active_runtime_map(db, source_id)
    return {
        "source_id": source_id,
        "runtime_map_source": runtime_map_source,
        "active_mapping_preset_id": source.active_mapping_preset_id,
        "runtime_mapping_updated_at": source.runtime_mapping_updated_at,
        "runtime_map": runtime_map,
    }


@router.get("/{source_id}/operations", response_model=dict)
async def get_source_operations(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    source = await _ensure_source(db, source_id)
    jobs = await crud.list_jobs(db, source_id=source_id, skip=0, limit=20)
    active_jobs = [job for job in jobs if job.status in {"queued", "pending", "running", "paused"}]

    pending_stmt = (
        select(func.count())
        .select_from(Record)
        .where(Record.source_id == source_id, Record.status == "needs_review")
    )
    pending_moderation = int((await db.execute(pending_stmt)).scalar_one() or 0)
    pending_duplicate_reviews = await crud.list_duplicate_reviews_for_source(db, source_id=source_id, status="pending", limit=10)

    return {
        "source": SourceDetailResponse.model_validate(source).model_dump(),
        "active_jobs": [_serialize_job_run(job) for job in active_jobs],
        "recent_runs": [_serialize_job_run(job) for job in jobs[:10]],
        "pending_moderation_count": pending_moderation + len(pending_duplicate_reviews),
        "pending_duplicate_review_count": len(pending_duplicate_reviews),
    }


@router.get("/{source_id}/runs", response_model=dict)
async def list_source_runs(
    source_id: str,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    await _ensure_source(db, source_id)
    runs = await crud.list_jobs(db, source_id=source_id, skip=0, limit=max(1, min(limit, 200)))
    return {"items": [_serialize_job_run(run) for run in runs], "total": len(runs)}


@router.get("/{source_id}/events", response_model=dict)
async def list_source_events(
    source_id: str,
    limit: int = 100,
    event_type: str | None = None,
    stage: str | None = None,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    await _ensure_source(db, source_id)
    jobs = await crud.list_jobs(db, source_id=source_id, skip=0, limit=500)
    job_ids = [job.id for job in jobs]
    if not job_ids:
        return {"items": [], "total": 0}

    stmt = select(JobEvent).where(JobEvent.source_id == source_id).order_by(JobEvent.timestamp.desc()).limit(max(1, min(limit, 500)))
    if event_type:
        stmt = stmt.where(JobEvent.event_type == event_type)
    if stage:
        stmt = stmt.where(JobEvent.stage == stage)
    events = (await db.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": event.id,
                "job_id": event.job_id,
                "source_id": event.source_id,
                "worker_id": event.worker_id,
                "timestamp": event.timestamp,
                "level": event.level,
                "event_type": event.event_type,
                "stage": event.stage,
                "message": event.message,
                "context": _parse_json(event.context, {}),
            }
            for event in reversed(list(events))
        ],
        "total": len(events),
    }


async def _ensure_source(db: AsyncSession, source_id: str):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


async def _enqueue_source_job(
    db: AsyncSession,
    *,
    source_id: str,
    job_type: str,
    payload: dict[str, object] | None = None,
) -> str:
    await _ensure_source(db, source_id)
    job = await crud.create_job(db, source_id=source_id, job_type=job_type, payload=payload or {})
    queue = get_default_queue()
    queue.enqueue(
        "app.pipeline.runner.process_pipeline_job",
        job.id,
        source_id,
        job_type,
        payload or {},
        job_timeout=900,
    )
    return job.id


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


@router.post("/{source_id}/run-deterministic-mine", response_model=dict, status_code=202)
async def run_deterministic_mine(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await _ensure_source(db, source_id)
    if not source.active_mapping_preset_id and not source.published_mapping_version_id:
        raise HTTPException(
            status_code=422,
            detail="Source has no active mapping — publish a draft or apply a preset before mining",
        )
    job_id = await _enqueue_source_job(
        db,
        source_id=source_id,
        job_type="mine_source_deterministic",
        payload={"runtime_mode": "deterministic"},
    )
    await crud.set_source_operational_status(db, source_id, "running", queue_paused=False, error_message=None)
    return {"job_id": job_id, "source_id": source_id, "status": "queued", "runtime_mode": "deterministic"}


@router.post("/{source_id}/run-enrichment", response_model=dict, status_code=202)
async def run_enrichment(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    job_id = await _enqueue_source_job(
        db,
        source_id=source_id,
        job_type="enrich_source_existing_pages",
        payload={"runtime_mode": "enrichment_only"},
    )
    await crud.set_source_operational_status(db, source_id, "running", queue_paused=False, error_message=None)
    return {"job_id": job_id, "source_id": source_id, "status": "queued", "runtime_mode": "enrichment_only"}


@router.post("/{source_id}/reprocess-existing-pages", response_model=dict, status_code=202)
async def reprocess_existing_pages(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    job_id = await _enqueue_source_job(
        db,
        source_id=source_id,
        job_type="reprocess_source_runtime_map",
        payload={"runtime_mode": "reprocess_existing_pages"},
    )
    await crud.set_source_operational_status(db, source_id, "running", queue_paused=False, error_message=None)
    return {"job_id": job_id, "source_id": source_id, "status": "queued", "runtime_mode": "reprocess_existing_pages"}


@router.get("/{source_id}/enrichment-summary", response_model=dict)
async def source_enrichment_summary(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    await _ensure_source(db, source_id)
    jobs = await crud.list_jobs(db, source_id=source_id, skip=0, limit=200)
    target_types = {"enrich_source_existing_pages", "reprocess_source_runtime_map", "mine_source_deterministic"}
    summary = {
        "source_id": source_id,
        "runs": 0,
        "records_created": 0,
        "records_updated": 0,
        "deterministic_hits": 0,
        "deterministic_misses": 0,
        "media_assets_captured": 0,
        "entity_links_created": 0,
    }
    for job in jobs:
        if job.job_type not in target_types:
            continue
        payload = _serialize_job_run(job)
        summary["runs"] += 1
        summary["records_created"] += int(payload.get("records_created", 0))
        summary["records_updated"] += int(payload.get("records_updated", 0))
        summary["deterministic_hits"] += int(payload.get("deterministic_hits", 0))
        summary["deterministic_misses"] += int(payload.get("deterministic_misses", 0))
        summary["media_assets_captured"] += int(payload.get("media_assets_captured", 0))
        summary["entity_links_created"] += int(payload.get("entity_links_created", 0))
    return summary


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


@router.post("/{source_id}/run", response_model=SourceActionResponse)
async def run_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    runtime_map, _runtime_map_source = await crud.get_active_runtime_map(db, source_id)
    if crud.has_usable_runtime_map_payload(runtime_map):
        job_id = await _enqueue_source_job(
            db,
            source_id=source_id,
            job_type="mine_source_deterministic",
            payload={"runtime_mode": "deterministic"},
        )
        source = await crud.set_source_operational_status(db, source_id, "running", queue_paused=False, error_message=None)
        return SourceActionResponse(
            source_id=source.id,
            status=source.status,
            operational_status=source.operational_status,
            queued_jobs=1 if job_id else 0,
        )
    return await start_full_mining_action(source_id=source_id, db=db, _role=_role)


@router.post("/{source_id}/pause", response_model=SourceActionResponse)
async def pause_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    return await pause_source_action(source_id=source_id, db=db, _role=_role)


@router.post("/{source_id}/resume", response_model=SourceActionResponse)
async def resume_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    return await resume_source_action(source_id=source_id, db=db, _role=_role)


@router.post("/{source_id}/cancel-active", response_model=SourceActionResponse)
async def cancel_source_active(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    return await stop_source_action(source_id=source_id, db=db, _role=_role)


@router.post("/{source_id}/backfill", response_model=SourceActionResponse)
async def backfill_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    await _ensure_source(db, source_id)
    job = await crud.create_job(db, source_id=source_id, job_type="run_backfill_campaign", payload={})
    source = await crud.set_source_operational_status(db, source_id, "running", queue_paused=False, error_message=None)
    return SourceActionResponse(
        source_id=source.id,
        status=source.status,
        operational_status=source.operational_status,
        queued_jobs=1 if job else 0,
    )


@router.get("/{source_id}/moderated-actions", response_model=dict)
async def list_source_moderated_actions(
    source_id: str,
    status: str = "pending",
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    await _ensure_source(db, source_id)
    reviews = await crud.list_duplicate_reviews_for_source(
        db,
        source_id=source_id,
        status=status if status else None,
        limit=max(1, min(limit, 200)),
    )
    items = []
    for review in reviews:
        left = await crud.get_record(db, review.left_record_id)
        right = await crud.get_record(db, review.right_record_id)
        items.append(
            {
                "id": review.id,
                "source_id": source_id,
                "status": review.status,
                "kind": "duplicate_review",
                "created_at": review.created_at,
                "similarity_score": review.similarity_score,
                "reason": review.reason,
                "left_record": {"id": left.id, "title": left.title, "record_type": left.record_type} if left else None,
                "right_record": {"id": right.id, "title": right.title, "record_type": right.record_type} if right else None,
                "reviewed_at": review.reviewed_at,
                "reviewed_by": review.reviewed_by,
            }
        )
    return {"items": items, "total": len(items)}


@router.post("/{source_id}/moderated-actions/{action_id}/approve", response_model=dict)
async def approve_source_moderated_action(
    source_id: str,
    action_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("merge")),
):
    await _ensure_source(db, source_id)
    review = await crud.get_duplicate_review(db, action_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Moderated action not found")
    left = await crud.get_record(db, review.left_record_id)
    right = await crud.get_record(db, review.right_record_id)
    if not left or not right or (left.source_id != source_id and right.source_id != source_id):
        raise HTTPException(status_code=404, detail="Moderated action not found for source")
    updated = await crud.set_duplicate_review_status(db, review_id=action_id, status="approved", reviewed_by="operator")
    return {"id": updated.id, "status": updated.status}


@router.post("/{source_id}/moderated-actions/{action_id}/reject", response_model=dict)
async def reject_source_moderated_action(
    source_id: str,
    action_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("merge")),
):
    await _ensure_source(db, source_id)
    review = await crud.get_duplicate_review(db, action_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Moderated action not found")
    left = await crud.get_record(db, review.left_record_id)
    right = await crud.get_record(db, review.right_record_id)
    if not left or not right or (left.source_id != source_id and right.source_id != source_id):
        raise HTTPException(status_code=404, detail="Moderated action not found for source")
    updated = await crud.set_duplicate_review_status(db, review_id=action_id, status="rejected", reviewed_by="operator")
    return {"id": updated.id, "status": updated.status}
