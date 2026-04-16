from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.db.models import BackfillCampaign, BackfillJob, BackfillSchedule, Record
from app.pipeline.backfill_processor import check_campaign_completion, enqueue_backfill_campaign
from app.queue import QueueUnavailableError
from app.services.backfill_query import BackfillQuery
from app.services.completeness import calculate_completeness

router = APIRouter(prefix="/backfill", tags=["backfill"])


class CampaignCreateRequest(BaseModel):
    name: str = Field(default="Backfill Campaign")
    strategy: str = Field(default="incomplete")
    record_type: str | None = None
    min_completeness: int = 0
    max_completeness: int = 70
    limit: int = 100
    dry_run: bool = False


class ScheduleCreateRequest(BaseModel):
    name: str
    schedule_type: str = Field(default="recurring")
    cron_expression: str | None = None
    filters: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)
    enabled: bool = True
    auto_start: bool = False


class ScheduleUpdateRequest(BaseModel):
    name: str | None = None
    schedule_type: str | None = None
    cron_expression: str | None = None
    filters: dict[str, object] | None = None
    options: dict[str, object] | None = None
    enabled: bool | None = None
    auto_start: bool | None = None


def _schedule_to_dict(schedule: BackfillSchedule) -> dict[str, object]:
    return {
        "id": schedule.id,
        "name": schedule.name,
        "schedule_type": schedule.schedule_type,
        "cron_expression": schedule.cron_expression,
        "filters": json.loads(schedule.filters_json),
        "options": json.loads(schedule.options_json),
        "enabled": schedule.enabled,
        "auto_start": schedule.auto_start,
        "last_run_at": schedule.last_run_at,
        "next_run_at": schedule.next_run_at,
        "created_at": schedule.created_at,
        "updated_at": schedule.updated_at,
    }


def _compute_next_run(cron_expression: str | None) -> datetime | None:
    if cron_expression is None:
        return None

    from croniter import croniter

    if not croniter.is_valid(cron_expression):
        raise HTTPException(status_code=400, detail="Invalid cron expression")

    return croniter(cron_expression, datetime.now(UTC)).get_next(datetime)


@router.get("/preview")
async def preview_backfill_candidates(
    record_type: str | None = None,
    min_completeness: int = Query(default=0, ge=0, le=100),
    max_completeness: int = Query(default=70, ge=0, le=100),
    limit: int = Query(default=25, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    if min_completeness > max_completeness:
        raise HTTPException(status_code=400, detail="min_completeness must be <= max_completeness")

    records = await BackfillQuery.find_incomplete_records(
        db=db,
        record_type=record_type,
        min_completeness=min_completeness,
        max_completeness=max_completeness,
        limit=limit,
    )
    items: list[dict] = []
    for record in records:
        completeness = calculate_completeness(record)
        items.append(
            {
                "record_id": record.id,
                "source_id": record.source_id,
                "record_type": record.record_type,
                "title": record.title,
                "source_url": record.source_url,
                "completeness_score": completeness["score"],
                "missing_fields": completeness["missing_fields"],
                "critical_missing": completeness["critical_missing"],
            }
        )

    return {
        "items": items,
        "total": len(items),
        "filters": {
            "record_type": record_type,
            "min_completeness": min_completeness,
            "max_completeness": max_completeness,
            "limit": limit,
        },
    }


@router.post("/campaigns")
async def create_backfill_campaign(
    payload: CampaignCreateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    records = await BackfillQuery.find_incomplete_records(
        db=db,
        record_type=payload.record_type,
        min_completeness=payload.min_completeness,
        max_completeness=payload.max_completeness,
        limit=payload.limit,
    )

    filters = {
        "record_type": payload.record_type,
        "min_completeness": payload.min_completeness,
        "max_completeness": payload.max_completeness,
    }
    options = {"limit": payload.limit, "dry_run": payload.dry_run}

    campaign = BackfillCampaign(
        name=payload.name,
        strategy=payload.strategy,
        filters_json=json.dumps(filters),
        options_json=json.dumps(options),
        status="dry_run" if payload.dry_run else "pending",
        total_records=len(records),
        processed_records=0,
        successful_updates=0,
        failed_updates=0,
        started_at=datetime.now(UTC) if not payload.dry_run else None,
    )
    db.add(campaign)
    await db.flush()

    jobs_created = 0
    if not payload.dry_run:
        for record in records:
            if not record.source_url:
                continue
            db.add(
                BackfillJob(
                    campaign_id=campaign.id,
                    record_id=record.id,
                    url_to_crawl=record.source_url,
                    status="pending",
                    before_completeness=record.completeness_score,
                )
            )
            jobs_created += 1

    await db.commit()

    return {
        "campaign_id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "total_candidates": len(records),
        "jobs_created": jobs_created,
        "dry_run": payload.dry_run,
    }


@router.post("/campaigns/{campaign_id}/start")
async def start_backfill_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    campaign = await db.get(BackfillCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == "dry_run":
        raise HTTPException(status_code=400, detail="Dry-run campaigns cannot be started")

    try:
        jobs_enqueued = await enqueue_backfill_campaign(db, campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (QueueUnavailableError, RedisError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Redis queue unavailable. Check that Redis server and workers are running.",
        ) from exc

    return {
        "campaign_id": campaign_id,
        "status": "running",
        "jobs_enqueued": jobs_enqueued,
        "message": f"Campaign started. {jobs_enqueued} jobs enqueued to workers.",
    }


@router.post("/campaigns/{campaign_id}/check-completion")
async def check_campaign_completion_endpoint(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    try:
        summary = await check_campaign_completion(db, campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    campaign = await db.get(BackfillCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {
        "campaign_id": campaign_id,
        "status": campaign.status,
        "processed": campaign.processed_records,
        "total": campaign.total_records,
        **summary,
    }


@router.get("/campaigns")
async def list_backfill_campaigns(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    result = await db.execute(
        select(BackfillCampaign).order_by(BackfillCampaign.created_at.desc()).offset(skip).limit(limit)
    )
    campaigns = result.scalars().all()
    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "strategy": c.strategy,
                "status": c.status,
                "total_records": c.total_records,
                "processed_records": c.processed_records,
                "successful_updates": c.successful_updates,
                "failed_updates": c.failed_updates,
                "created_at": c.created_at,
                "started_at": c.started_at,
                "completed_at": c.completed_at,
            }
            for c in campaigns
        ],
        "total": len(campaigns),
        "skip": skip,
        "limit": limit,
    }


@router.get("/campaigns/{campaign_id}")
async def get_backfill_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    campaign = await db.get(BackfillCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    jobs_result = await db.execute(select(BackfillJob).where(BackfillJob.campaign_id == campaign_id))
    jobs = jobs_result.scalars().all()

    return {
        "id": campaign.id,
        "name": campaign.name,
        "strategy": campaign.strategy,
        "status": campaign.status,
        "filters": json.loads(campaign.filters_json),
        "options": json.loads(campaign.options_json),
        "total_records": campaign.total_records,
        "processed_records": campaign.processed_records,
        "successful_updates": campaign.successful_updates,
        "failed_updates": campaign.failed_updates,
        "jobs": [
            {
                "id": j.id,
                "record_id": j.record_id,
                "url_to_crawl": j.url_to_crawl,
                "status": j.status,
                "before_completeness": j.before_completeness,
                "after_completeness": j.after_completeness,
                "attempts": j.attempts,
                "error_message": j.error_message,
            }
            for j in jobs
        ],
    }


@router.post("/calculate-completeness")
async def calculate_existing_completeness(
    record_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    stmt = select(Record)
    if record_type:
        stmt = stmt.where(Record.record_type == record_type)

    result = await db.execute(stmt)
    records = result.scalars().all()
    updated = 0
    for record in records:
        details = calculate_completeness(record)
        record.completeness_score = details["score"]
        record.completeness_details = json.dumps(
            {
                "missing_fields": details["missing_fields"],
                "critical_missing": details["critical_missing"],
            }
        )
        updated += 1

    await db.commit()
    return {"updated": updated, "record_type": record_type}


@router.get("/schedules")
async def list_backfill_schedules(
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    result = await db.execute(select(BackfillSchedule).order_by(BackfillSchedule.created_at.desc()))
    schedules = result.scalars().all()
    return {"items": [_schedule_to_dict(schedule) for schedule in schedules], "total": len(schedules)}


@router.post("/schedules")
async def create_backfill_schedule(
    payload: ScheduleCreateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    next_run_at = _compute_next_run(payload.cron_expression)
    schedule = BackfillSchedule(
        name=payload.name,
        schedule_type=payload.schedule_type,
        cron_expression=payload.cron_expression,
        filters_json=json.dumps(payload.filters),
        options_json=json.dumps(payload.options),
        enabled=payload.enabled,
        auto_start=payload.auto_start,
        next_run_at=next_run_at,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return _schedule_to_dict(schedule)


@router.patch("/schedules/{schedule_id}")
async def update_backfill_schedule(
    schedule_id: str,
    payload: ScheduleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    schedule = await db.get(BackfillSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    patch_data = payload.model_dump(exclude_unset=True)
    if "name" in patch_data:
        schedule.name = patch_data["name"]
    if "schedule_type" in patch_data:
        schedule.schedule_type = patch_data["schedule_type"]
    if "cron_expression" in patch_data:
        schedule.cron_expression = patch_data["cron_expression"]
        schedule.next_run_at = _compute_next_run(schedule.cron_expression)
    if "filters" in patch_data:
        schedule.filters_json = json.dumps(patch_data["filters"])
    if "options" in patch_data:
        schedule.options_json = json.dumps(patch_data["options"])
    if "enabled" in patch_data:
        schedule.enabled = patch_data["enabled"]
    if "auto_start" in patch_data:
        schedule.auto_start = patch_data["auto_start"]

    await db.commit()
    await db.refresh(schedule)
    return _schedule_to_dict(schedule)


@router.delete("/schedules/{schedule_id}")
async def delete_backfill_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("manage_jobs")),
):
    schedule = await db.get(BackfillSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await db.delete(schedule)
    await db.commit()
    return {"deleted": True, "schedule_id": schedule_id}
