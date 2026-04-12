import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import Job

logger = structlog.get_logger()


class PipelineQueue:
    async def enqueue(
        self,
        source_id: str,
        job_type: str,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> Job:
        """Create and enqueue a new job."""
        job = await crud.create_job(db, source_id=source_id, job_type=job_type, payload=payload)
        logger.info("job_enqueued", job_id=job.id, job_type=job_type, source_id=source_id)
        return job

    async def process_next(
        self,
        db: AsyncSession,
        runners: dict[str, Callable],
    ) -> Job | None:
        """Fetch and process the next pending job."""
        job = await crud.get_next_pending_job(db)
        if job is None:
            return None

        # Mark as running
        job = await crud.update_job_status(
            db, job.id, "running", started_at=datetime.utcnow(), attempts=job.attempts + 1
        )
        logger.info("job_started", job_id=job.id, job_type=job.job_type)

        runner = runners.get(job.job_type)
        if runner is None:
            logger.error("no_runner_for_job_type", job_type=job.job_type)
            await crud.update_job_status(
                db,
                job.id,
                "failed",
                error_message=f"No runner for job type: {job.job_type}",
                completed_at=datetime.utcnow(),
            )
            return job

        try:
            payload = json.loads(job.payload or "{}")
            result = await runner(job.source_id, payload)
            await crud.update_job_status(
                db,
                job.id,
                "done",
                result=result if isinstance(result, dict) else {"result": str(result)},
                completed_at=datetime.utcnow(),
            )
            logger.info("job_done", job_id=job.id)
        except Exception as exc:
            logger.error("job_failed", job_id=job.id, error=str(exc))
            new_status = "failed" if job.attempts >= job.max_attempts else "pending"
            await crud.update_job_status(
                db,
                job.id,
                new_status,
                error_message=str(exc),
                completed_at=datetime.utcnow() if new_status == "failed" else None,
            )

        return job
