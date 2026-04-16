from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.db import crud
from app.db.models import DuplicateReview, EntityRelationship, Job, Record

router = APIRouter(tags=["operations"])


def _job_status_external(status: str) -> str:
    return "completed" if status == "done" else status


def _parse_json(payload: str | None, default: Any) -> Any:
    if payload is None:
        return default
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return default


def _duration_seconds(job: Job) -> int | None:
    if not job.started_at:
        return None
    end = job.completed_at or datetime.now(UTC)
    return max(0, int((end - job.started_at).total_seconds()))


def _progress_percent(job: Job) -> int | None:
    if job.progress_total and job.progress_total > 0:
        return int((job.progress_current / job.progress_total) * 100)
    return None


def _is_job_stale(job: Job) -> bool:
    if job.status != "running" or job.last_heartbeat_at is None:
        return False
    return (datetime.now(UTC) - job.last_heartbeat_at) > timedelta(minutes=2)


def _serialize_job(job: Job, source_name: str | None) -> dict[str, Any]:
    return {
        "id": job.id,
        "source_id": job.source_id,
        "source": source_name,
        "job_type": job.job_type,
        "status": _job_status_external(job.status),
        "worker_id": job.worker_id,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "payload": _parse_json(job.payload, {}),
        "error_message": job.error_message,
        "processed_count": int(_parse_json(job.result, {}).get("processed_count", 0)),
        "failure_count": int(_parse_json(job.result, {}).get("failure_count", 0)) + (1 if job.error_message else 0),
        "duration_seconds": _duration_seconds(job),
        "current_stage": job.current_stage,
        "stage": job.current_stage,
        "current_item": job.current_item,
        "item": job.current_item,
        "progress_current": job.progress_current,
        "progress_total": job.progress_total,
        "progress": {"current": job.progress_current, "total": job.progress_total},
        "progress_percent": _progress_percent(job),
        "last_heartbeat_at": job.last_heartbeat_at,
        "heartbeat": job.last_heartbeat_at,
        "last_log_message": job.last_log_message,
        "metrics": _parse_json(job.metrics_json, {}),
        "is_stale": _is_job_stale(job),
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "created_at": job.created_at,
    }


@router.get("/jobs")
async def list_jobs(
    source_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    jobs = await crud.list_jobs(db, source_id=source_id, status=status, skip=skip, limit=limit)
    source_map = {source.id: source for source in await crud.list_sources(db, skip=0, limit=1000)}
    return {
        "items": [_serialize_job(job, source_map.get(job.source_id).name if source_map.get(job.source_id) else None) for job in jobs],
        "total": len(jobs),
        "skip": skip,
        "limit": limit,
    }


@router.get("/jobs/{job_id}")
async def get_job_detail(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    job = await crud.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    source = await crud.get_source(db, job.source_id)
    payload = _serialize_job(job, source.name if source else None)
    payload["result"] = _parse_json(job.result, {})
    return payload


@router.get("/jobs/{job_id}/events")
async def get_job_events(
    job_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    job = await crud.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    events = await crud.list_job_events(db, job_id, limit=limit)
    events = list(reversed(events))
    return {
        "items": [
            {
                "id": event.id,
                "timestamp": event.timestamp,
                "level": event.level,
                "event_type": event.event_type,
                "worker_id": event.worker_id,
                "stage": event.stage,
                "message": event.message,
                "context": _parse_json(event.context, {}),
            }
            for event in events
        ],
        "total": len(events),
    }


@router.get("/workers")
async def list_workers(
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    workers = await crud.list_worker_states(db)
    return {
        "items": [
            {
                "worker_id": worker.worker_id,
                "status": worker.status,
                "current_job_id": worker.current_job_id,
                "stage": worker.current_stage,
                "heartbeat": worker.last_heartbeat_at,
                "metrics": _parse_json(worker.metrics_json, {}),
            }
            for worker in workers
        ],
        "total": len(workers),
    }


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    job = await crud.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in {"failed", "cancelled"}:
        raise HTTPException(status_code=400, detail="Only failed/cancelled jobs can be retried")

    updated = await crud.update_job_status(
        db,
        job.id,
        "pending",
        attempts=job.attempts + 1,
        error_message=None,
        started_at=None,
        completed_at=None,
    )
    return {"id": updated.id, "status": _job_status_external(updated.status)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    job = await crud.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in {"done", "completed", "failed", "cancelled"}:
        raise HTTPException(status_code=400, detail="Job is already terminal")
    updated = await crud.update_job_status(db, job.id, "cancelled", completed_at=datetime.now(UTC))
    return {"id": updated.id, "status": _job_status_external(updated.status)}


@router.post("/jobs/{job_id}/pause")
async def pause_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    job = await crud.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in {"queued", "pending", "running"}:
        raise HTTPException(status_code=400, detail="Only queued/pending/running jobs can be paused")
    updated = await crud.update_job_status(db, job.id, "paused")
    return {"id": updated.id, "status": _job_status_external(updated.status)}


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    job = await crud.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "paused":
        raise HTTPException(status_code=400, detail="Only paused jobs can be resumed")
    updated = await crud.update_job_status(db, job.id, "pending")
    return {"id": updated.id, "status": _job_status_external(updated.status)}


@router.get("/queues")
async def get_queues(
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    jobs = await crud.list_jobs(db, skip=0, limit=5000)
    now = datetime.now(UTC)
    oldest_pending_age = 0
    for job in jobs:
        if job.status in {"queued", "pending"}:
            created_at = job.created_at
            if created_at is None:
                continue
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            oldest_pending_age = max(oldest_pending_age, int((now - created_at).total_seconds()))

    paused_sources = await crud.list_sources(db, skip=0, limit=1000, enabled=True)
    paused_count = len([s for s in paused_sources if getattr(s, "queue_paused", False)])
    return {
        "items": [
            {
                "name": "default",
                "pending": len([j for j in jobs if j.status in {"queued", "pending"}]),
                "running": len([j for j in jobs if j.status == "running"]),
                "failed": len([j for j in jobs if j.status == "failed"]),
                "paused": paused_count,
                "oldest_item_age_seconds": oldest_pending_age,
            }
        ],
        "total": 1,
    }


@router.post("/queues/{name}/pause")
async def pause_queue(
    name: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    if name != "default":
        raise HTTPException(status_code=404, detail="Queue not found")
    sources = await crud.list_sources(db, skip=0, limit=1000, enabled=True)
    for source in sources:
        await crud.update_source(db, source.id, queue_paused=True, operational_status="paused", status="paused")
    return {"name": name, "status": "paused"}


@router.post("/queues/{name}/resume")
async def resume_queue(
    name: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    if name != "default":
        raise HTTPException(status_code=404, detail="Queue not found")
    sources = await crud.list_sources(db, skip=0, limit=1000, enabled=True)
    for source in sources:
        if source.queue_paused:
            await crud.update_source(db, source.id, queue_paused=False, operational_status="idle", status="idle")
    return {"name": name, "status": "running"}


@router.get("/queues/review")
async def get_review_queue(
    type: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    queue_type = type.lower()
    items: list[dict[str, Any]] = []

    if queue_type == "conflicts":
        stmt = (
            select(Record)
            .where(and_(Record.has_conflicts.is_(True), Record.status == "pending"))
            .order_by(Record.completeness_score.asc(), Record.updated_at.desc())
            .limit(limit)
        )
        records = (await db.execute(stmt)).scalars().all()
        items = [
            {
                "id": record.id,
                "source_id": record.source_id,
                "title": record.title,
                "record_type": record.record_type,
                "priority": max(1, 100 - int(record.completeness_score or 0)),
                "updated_at": record.updated_at,
            }
            for record in records
        ]
    elif queue_type == "duplicates":
        reviews = await crud.list_duplicate_reviews(db, status="pending", limit=limit)
        for review in reviews:
            left = await crud.get_record(db, review.left_record_id)
            right = await crud.get_record(db, review.right_record_id)
            items.append(
                {
                    "id": review.id,
                    "left_id": review.left_record_id,
                    "right_id": review.right_record_id,
                    "left_title": left.title if left else None,
                    "right_title": right.title if right else None,
                    "similarity_score": review.similarity_score,
                    "priority": review.similarity_score,
                    "created_at": review.created_at,
                }
            )
    elif queue_type == "completeness":
        stmt = (
            select(Record)
            .where(Record.status == "pending")
            .order_by(Record.completeness_score.asc(), Record.updated_at.desc())
            .limit(limit)
        )
        records = (await db.execute(stmt)).scalars().all()
        items = [
            {
                "id": record.id,
                "source_id": record.source_id,
                "title": record.title,
                "record_type": record.record_type,
                "completeness_score": record.completeness_score,
                "priority": max(1, 100 - int(record.completeness_score or 0)),
            }
            for record in records
        ]
    elif queue_type == "recent":
        stmt = select(Record).order_by(Record.updated_at.desc()).limit(limit)
        records = (await db.execute(stmt)).scalars().all()
        items = [
            {
                "id": record.id,
                "source_id": record.source_id,
                "title": record.title,
                "record_type": record.record_type,
                "updated_at": record.updated_at,
                "priority": 1,
            }
            for record in records
        ]
    else:
        raise HTTPException(status_code=400, detail="Unsupported queue type")

    return {"type": queue_type, "items": items, "total": len(items)}


@router.post("/schedule")
async def create_schedule(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("schedule")),
):
    cron_expr = str(body.get("cron") or "").strip()
    job_type = str(body.get("job_type") or "").strip()
    source_id = body.get("source_id")
    if not cron_expr or not job_type:
        raise HTTPException(status_code=400, detail="'cron' and 'job_type' are required")
    if source_id:
        source = await crud.get_source(db, source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Source not found")

    scheduled = await crud.create_scheduled_job(
        db,
        source_id=source_id,
        job_type=job_type,
        cron_expr=cron_expr,
        payload=body.get("payload") if isinstance(body.get("payload"), dict) else {},
        enabled=bool(body.get("enabled", True)),
    )
    return {
        "id": scheduled.id,
        "source_id": scheduled.source_id,
        "job_type": scheduled.job_type,
        "cron": scheduled.cron_expr,
        "payload": _parse_json(scheduled.payload, {}),
        "enabled": scheduled.enabled,
    }


@router.get("/schedule")
async def list_schedule(
    source_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    entries = await crud.list_scheduled_jobs(db, source_id=source_id)
    return {
        "items": [
            {
                "id": entry.id,
                "source_id": entry.source_id,
                "job_type": entry.job_type,
                "cron": entry.cron_expr,
                "payload": _parse_json(entry.payload, {}),
                "enabled": entry.enabled,
                "last_run_at": entry.last_run_at,
                "next_run_at": entry.next_run_at,
            }
            for entry in entries
        ],
        "total": len(entries),
    }


@router.get("/metrics/history")
async def metrics_history(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    days = max(1, min(days, 365))
    today = date.today()
    start = today - timedelta(days=days - 1)

    results: list[dict[str, Any]] = []
    for offset in range(days):
        bucket = start + timedelta(days=offset)
        day_start = datetime.combine(bucket, datetime.min.time(), tzinfo=UTC)
        day_end = day_start + timedelta(days=1)

        created_records = (
            await db.execute(
                select(func.count(Record.id)).where(Record.created_at >= day_start, Record.created_at < day_end)
            )
        ).scalar_one()
        duplicate_reviews = (
            await db.execute(
                select(func.count(DuplicateReview.id)).where(
                    DuplicateReview.created_at >= day_start,
                    DuplicateReview.created_at < day_end,
                )
            )
        ).scalar_one()
        merge_actions = await crud.count_audit_actions(db, action_type="merge")
        successful_crawls = (
            await db.execute(
                select(func.count(Job.id)).where(
                    Job.job_type == "crawl_section",
                    Job.status.in_(["done", "completed"]),
                    Job.created_at >= day_start,
                    Job.created_at < day_end,
                )
            )
        ).scalar_one()
        total_crawls = (
            await db.execute(
                select(func.count(Job.id)).where(
                    Job.job_type == "crawl_section",
                    Job.created_at >= day_start,
                    Job.created_at < day_end,
                )
            )
        ).scalar_one()

        avg_completeness = (
            await db.execute(
                select(func.avg(Record.completeness_score)).where(
                    Record.updated_at >= day_start,
                    Record.updated_at < day_end,
                )
            )
        ).scalar_one()

        entry = {
            "date": bucket.isoformat(),
            "completeness_avg": round(float(avg_completeness or 0), 2),
            "merge_rate": int(merge_actions),
            "duplicate_detection_rate": int(duplicate_reviews),
            "crawl_success_rate": round((successful_crawls / total_crawls) if total_crawls else 0, 4),
            "records_created": int(created_records),
        }
        results.append(entry)
        await crud.upsert_metric_snapshot(db, bucket_date=bucket.isoformat(), metrics=entry)

    return {"items": results, "total": len(results)}


@router.post("/merge/{merge_id}/rollback")
async def rollback_merge(
    merge_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    history = await crud.get_merge_history(db, merge_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Merge history not found")
    if history.rolled_back:
        raise HTTPException(status_code=400, detail="Merge already rolled back")

    primary_snapshot = _parse_json(history.primary_snapshot, {})
    secondary_snapshot = _parse_json(history.secondary_snapshot, {})
    relationships = _parse_json(history.relationships_snapshot, [])

    primary = await crud.get_record(db, history.primary_record_id)
    if primary is None:
        raise HTTPException(status_code=404, detail="Primary record missing; cannot rollback")

    restore_fields = {
        key: value
        for key, value in primary_snapshot.items()
        if key not in {"id", "created_at", "updated_at"}
    }
    await crud.update_record(db, primary.id, **restore_fields)

    recreated_secondary = Record(
        **{
            key: value
            for key, value in secondary_snapshot.items()
            if key not in {"created_at", "updated_at"}
        }
    )
    db.add(recreated_secondary)
    await db.commit()

    for relation in relationships:
        await crud.upsert_entity_relationship(
            db,
            source_id=relation.get("source_id"),
            from_record_id=relation.get("from_record_id"),
            to_record_id=relation.get("to_record_id"),
            relationship_type=relation.get("relationship_type"),
            metadata=relation.get("metadata_json") or {},
        )

    await crud.mark_merge_history_rolled_back(db, merge_id)
    await crud.create_audit_action(
        db,
        action_type="merge_rollback",
        source_id=history.source_id,
        record_id=history.primary_record_id,
        affected_record_ids=[history.primary_record_id, history.secondary_record_id],
        details={"merge_id": merge_id},
    )

    return {
        "merge_id": merge_id,
        "status": "rolled_back",
        "restored_secondary_id": history.secondary_record_id,
    }
