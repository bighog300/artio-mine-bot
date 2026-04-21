from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud


async def resume_crawl_run(db: AsyncSession, *, crawl_run_id: str) -> dict[str, Any]:
    crawl_run = await crud.get_crawl_run(db, crawl_run_id)
    if crawl_run is None:
        raise ValueError("Crawl run not found")

    if crawl_run.status == "completed":
        return {"crawl_run_id": crawl_run.id, "status": crawl_run.status, "requeued": 0}

    requeued_discovered = await crud.queue_discovered_frontier_rows(db, crawl_run_id=crawl_run_id, limit=10000)
    requeued_retryable = await crud.requeue_retryable_frontier_rows(db, crawl_run_id=crawl_run_id, limit=10000)
    crawl_run = await crud.update_crawl_run(db, crawl_run_id, status="running", cooldown_until=None)

    counts = await crud.get_crawl_frontier_counts(db, crawl_run_id)
    await crud.upsert_crawl_run_checkpoint(
        db,
        crawl_run_id=crawl_run.id,
        source_id=crawl_run.source_id,
        mapping_version_id=crawl_run.mapping_version_id,
        status="running",
        frontier_counts=counts,
        progress={"resume_requested": True},
        worker_state={"trigger": "api_resume"},
    )
    await crud.update_source(db, crawl_run.source_id, queue_paused=False, operational_status="running")
    return {
        "crawl_run_id": crawl_run.id,
        "status": crawl_run.status,
        "mapping_version_id": crawl_run.mapping_version_id,
        "requeued": requeued_discovered + requeued_retryable,
    }
