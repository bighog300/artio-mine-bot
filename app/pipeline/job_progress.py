from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.log_writer import log_stream_manager


async def report_job_progress(
    db: AsyncSession,
    job_id: str,
    *,
    source_id: str | None = None,
    stage: str | None = None,
    item: str | None = None,
    message: str | None = None,
    progress_current: int | None = None,
    progress_total: int | None = None,
    metrics: dict[str, Any] | None = None,
    event_type: str = "progress",
    level: str = "info",
) -> None:
    updated = await crud.update_job_progress(
        db,
        job_id,
        stage=stage,
        item=item,
        progress_current=progress_current,
        progress_total=progress_total,
        last_log_message=message,
        metrics=metrics,
        heartbeat=True,
    )
    if updated is None:
        return

    event = await crud.append_job_event(
        db,
        job_id=job_id,
        source_id=source_id,
        event_type=event_type,
        message=message or event_type,
        level=level,
        stage=stage,
        context={
            "item": item,
            "progress_current": progress_current,
            "progress_total": progress_total,
            "metrics": metrics,
        },
    )

    await log_stream_manager.publish(
        {
            "stream_type": "job_progress",
            "job_id": job_id,
            "source_id": source_id,
            "stage": stage,
            "message": message,
            "progress_current": progress_current,
            "progress_total": progress_total,
            "event_type": event_type,
            "level": level,
            "timestamp": event.timestamp.isoformat(),
        }
    )
