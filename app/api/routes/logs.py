import asyncio
import json
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.log_writer import delete_logs, list_logs, log_stream_manager

router = APIRouter(prefix="/logs", tags=["logs"])
logger = structlog.get_logger()


@router.get("")
async def get_logs(
    level: str | None = Query(default=None),
    service: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_logs(
        db,
        level=level,
        service=service,
        source_id=source_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )

    return {
        "items": [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "level": log.level,
                "service": log.service,
                "source_id": log.source_id,
                "message": log.message,
                "context": log.context,
            }
            for log in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/activity")
async def get_activity(
    limit: int = Query(default=20, ge=1, le=100),
    source_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    activity_tokens = {
        "record_created",
        "pipeline_complete",
        "pipeline_error",
        "crawl_stage_error",
        "extraction_started",
        "pages_processed",
    }
    try:
        # Limit before filtering to avoid expensive scans.
        items, _ = await list_logs(
            db,
            source_id=source_id,
            level=None,
            service=None,
            search=None,
            date_from=None,
            date_to=None,
            skip=0,
            limit=min(limit * 5, 100),
        )
        activity = [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "level": log.level,
                "service": log.service,
                "source_id": log.source_id,
                "message": log.message,
                "context": log.context,
            }
            for log in items
            if any(token in (log.message or "") for token in activity_tokens)
        ]
        return {"items": activity[:limit]}
    except SQLAlchemyError as exc:
        logger.error(
            "activity_logs_db_error",
            limit=limit,
            offset=0,
            source_id=source_id,
            error=str(exc),
        )
        return {"items": []}


@router.delete("")
async def purge_logs(
    older_than_days: int = Query(default=30, ge=0),
    level: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    deleted_count = await delete_logs(db, older_than_days=older_than_days, level=level)
    return {"deleted_count": deleted_count}


@router.get("/stream")
async def stream_logs(request: Request):
    queue = log_stream_manager.subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            log_stream_manager.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
