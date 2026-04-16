"""Background scheduler for automated backfill campaigns."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import structlog
from croniter import croniter
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import BackfillCampaign, BackfillSchedule
from app.pipeline.backfill_processor import enqueue_backfill_campaign
from app.services.backfill_query import BackfillQuery

logger = structlog.get_logger()


class BackfillScheduler:
    """Periodic runner that converts schedules into campaigns."""

    def __init__(self) -> None:
        self.running = False

    async def check_schedules(self) -> int:
        """Create and optionally enqueue campaigns for all due schedules."""
        executed = 0
        async with AsyncSessionLocal() as db:
            now = datetime.now(UTC)
            result = await db.execute(
                select(BackfillSchedule).where(
                    BackfillSchedule.enabled.is_(True),
                    BackfillSchedule.next_run_at.is_not(None),
                    BackfillSchedule.next_run_at <= now,
                )
            )
            schedules = result.scalars().all()

            for schedule in schedules:
                await self._execute_schedule(schedule.id)
                executed += 1

        return executed

    async def _execute_schedule(self, schedule_id: str) -> None:
        async with AsyncSessionLocal() as db:
            schedule = await db.get(BackfillSchedule, schedule_id)
            if schedule is None or not schedule.enabled:
                return

            filters = json.loads(schedule.filters_json)
            options = json.loads(schedule.options_json)

            records = await BackfillQuery.find_incomplete_records(
                db=db,
                record_type=filters.get("record_type"),
                min_completeness=int(filters.get("min_completeness", 0)),
                max_completeness=int(filters.get("max_completeness", 70)),
                limit=int(options.get("limit", 100)),
            )

            campaign = BackfillCampaign(
                name=f"{schedule.name} - {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}",
                strategy="scheduled",
                filters_json=schedule.filters_json,
                options_json=schedule.options_json,
                status="pending",
                total_records=len(records),
                processed_records=0,
                successful_updates=0,
                failed_updates=0,
            )
            db.add(campaign)

            schedule.last_run_at = datetime.now(UTC)
            if schedule.cron_expression:
                schedule.next_run_at = croniter(schedule.cron_expression, datetime.now(UTC)).get_next(datetime)

            await db.commit()
            await db.refresh(campaign)

            if schedule.auto_start:
                await enqueue_backfill_campaign(db, campaign.id)

            logger.info(
                "backfill_schedule_executed",
                schedule_id=schedule.id,
                campaign_id=campaign.id,
                total_records=campaign.total_records,
                auto_start=schedule.auto_start,
            )

    async def start(self) -> None:
        """Run schedule polling loop until stopped."""
        self.running = True
        logger.info("backfill_scheduler_started")

        while self.running:
            try:
                executed = await self.check_schedules()
                logger.debug("backfill_scheduler_tick", schedules_executed=executed)
            except Exception:
                logger.exception("backfill_scheduler_tick_failed")
            await asyncio.sleep(60)

    def stop(self) -> None:
        self.running = False


async def run_scheduler() -> None:
    scheduler = BackfillScheduler()
    await scheduler.start()


if __name__ == "__main__":
    asyncio.run(run_scheduler())
