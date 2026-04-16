from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.db.models import BackfillCampaign, BackfillJob, Record
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
