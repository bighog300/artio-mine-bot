from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.db import crud
from app.db.log_writer import log_stream_manager
from app.db.models import CrawlFrontier, Page, Record

router = APIRouter(tags=["crawl-runs"])


def _as_sse(event_type: str, payload: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"


@router.get("/sources/{source_id}/crawl-runs")
async def list_source_crawl_runs(
    source_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    rows = await crud.list_crawl_runs(db, source_id, limit=limit)
    return {
        "items": [
            {
                "id": row.id,
                "source_id": row.source_id,
                "job_id": row.job_id,
                "status": row.status,
                "seed_url": row.seed_url,
                "worker_id": row.worker_id,
                "attempt": row.attempt,
                "cooldown_until": row.cooldown_until,
                "started_at": row.started_at,
                "completed_at": row.completed_at,
                "last_heartbeat_at": row.last_heartbeat_at,
                "stats": json.loads(row.stats_json or "{}"),
                "error_message": row.error_message,
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/crawl-runs/{crawl_run_id}")
async def get_crawl_run_detail(
    crawl_run_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    row = await crud.get_crawl_run(db, crawl_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Crawl run not found")
    counts = await crud.get_crawl_frontier_counts(db, crawl_run_id)
    records_created = await crud.count_records(db, source_id=row.source_id)
    pages_visible = await crud.count_pages(db, source_id=row.source_id)
    return {
        "crawl_run_id": row.id,
        "status": row.status,
        "queued_count": counts.get("queued", 0),
        "leased_count": counts.get("leased", 0),
        "fetched_count": counts.get("fetched", 0),
        "skipped_count": counts.get("skipped", 0),
        "error_count": counts.get("error", 0),
        "rate_limited_count": counts.get("rate_limited", 0),
        "records_created": records_created,
        "records_updated": 0,
        "pages_visible": pages_visible,
        "last_event_at": row.updated_at,
        "cooldown_until": row.cooldown_until,
    }


@router.get("/crawl-runs/{crawl_run_id}/frontier")
async def get_crawl_run_frontier(
    crawl_run_id: str,
    status: str | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    stmt = select(CrawlFrontier).where(CrawlFrontier.crawl_run_id == crawl_run_id)
    if status:
        stmt = stmt.where(CrawlFrontier.status == status)
    stmt = stmt.order_by(CrawlFrontier.updated_at.desc()).limit(limit)
    rows = list((await db.execute(stmt)).scalars().all())
    return {
        "items": [
            {
                "id": row.id,
                "url": row.url,
                "normalized_url": row.normalized_url,
                "depth": row.depth,
                "status": row.status,
                "retry_count": row.retry_count,
                "next_retry_at": row.next_retry_at,
                "last_status_code": row.last_status_code,
                "last_error": row.last_error,
                "leased_by_worker": row.leased_by_worker,
                "lease_expires_at": row.lease_expires_at,
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/crawl-runs/{crawl_run_id}/pages")
async def get_crawl_run_pages(
    crawl_run_id: str,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    rows = list((await db.execute(select(Page).where(Page.crawl_run_id == crawl_run_id).order_by(Page.created_at.desc()).limit(limit))).scalars().all())
    return {"items": [{"id": p.id, "url": p.url, "status": p.status, "title": p.title, "crawled_at": p.crawled_at} for p in rows], "total": len(rows)}


@router.get("/crawl-runs/{crawl_run_id}/records")
async def get_crawl_run_records(
    crawl_run_id: str,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    rows = list((await db.execute(select(Record).where(Record.crawl_run_id == crawl_run_id).order_by(Record.created_at.desc()).limit(limit))).scalars().all())
    return {"items": [{"id": r.id, "record_type": r.record_type, "title": r.title, "status": r.status} for r in rows], "total": len(rows)}


@router.post("/crawl-runs/{crawl_run_id}/pause")
async def pause_crawl_run(crawl_run_id: str, db: AsyncSession = Depends(get_db), _role: str = Depends(require_permission("manage_jobs"))):
    row = await crud.update_crawl_run(db, crawl_run_id, status="paused")
    await crud.update_source(db, row.source_id, queue_paused=True, operational_status="paused")
    return {"id": row.id, "status": row.status}


@router.post("/crawl-runs/{crawl_run_id}/resume")
async def resume_crawl_run(crawl_run_id: str, db: AsyncSession = Depends(get_db), _role: str = Depends(require_permission("manage_jobs"))):
    row = await crud.update_crawl_run(db, crawl_run_id, status="running", cooldown_until=None)
    await crud.update_source(db, row.source_id, queue_paused=False, operational_status="running")
    return {"id": row.id, "status": row.status}


@router.post("/crawl-runs/{crawl_run_id}/cancel")
async def cancel_crawl_run(crawl_run_id: str, db: AsyncSession = Depends(get_db), _role: str = Depends(require_permission("manage_jobs"))):
    row = await crud.update_crawl_run(db, crawl_run_id, status="cancelled", completed_at=datetime.now(UTC))
    await crud.update_source(db, row.source_id, queue_paused=True, operational_status="stopping")
    return {"id": row.id, "status": row.status}


@router.post("/crawl-runs/{crawl_run_id}/reclaim-stale")
async def reclaim_crawl_run_stale(crawl_run_id: str, db: AsyncSession = Depends(get_db), _role: str = Depends(require_permission("manage_jobs"))):
    row = await crud.get_crawl_run(db, crawl_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Crawl run not found")
    reclaimed = await crud.reclaim_expired_frontier_leases(db, crawl_run_id=crawl_run_id)
    await crud.update_crawl_run(db, crawl_run_id, status="running", last_heartbeat_at=datetime.now(UTC))
    return {"crawl_run_id": crawl_run_id, "reclaimed": reclaimed}


@router.get("/crawl-runs/{crawl_run_id}/stream")
async def stream_crawl_run(
    crawl_run_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    row = await crud.get_crawl_run(db, crawl_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Crawl run not found")

    async def event_stream():
        queue = log_stream_manager.subscribe()
        try:
            yield _as_sse("heartbeat", {"crawl_run_id": crawl_run_id, "timestamp": datetime.now(UTC).isoformat()})
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    if event.get("stream_type") == "job_progress":
                        metrics = event.get("metrics") or {}
                        if metrics.get("crawl_run_id") == crawl_run_id:
                            yield _as_sse(event.get("event_type", "progress"), event)
                except TimeoutError:
                    refreshed = await crud.get_crawl_run(db, crawl_run_id)
                    if refreshed is None or refreshed.status in {"completed", "failed", "cancelled"}:
                        yield _as_sse("complete", {"crawl_run_id": crawl_run_id})
                        break
                    yield _as_sse("heartbeat", {"crawl_run_id": crawl_run_id, "timestamp": datetime.now(UTC).isoformat()})
        finally:
            log_stream_manager.unsubscribe(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
