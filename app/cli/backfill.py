from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime

from croniter import croniter
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import BackfillCampaign, BackfillJob, BackfillSchedule
from app.services.backfill_query import BackfillQuery
from app.services.completeness import calculate_completeness


async def cmd_incomplete(args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as db:
        records = await BackfillQuery.find_incomplete_records(
            db=db,
            record_type=args.record_type,
            min_completeness=args.min_completeness,
            max_completeness=args.max_completeness,
            limit=args.limit,
        )

        if args.dry_run:
            for record in records:
                c = calculate_completeness(record)
                print(
                    f"- {record.id} [{record.record_type}] score={c['score']} title={record.title!r} "
                    f"url={record.source_url} missing={','.join(c['missing_fields'])}"
                )
            print(f"Total candidates: {len(records)}")
            return

        campaign = BackfillCampaign(
            name=args.name,
            strategy="incomplete",
            filters_json=json.dumps(
                {
                    "record_type": args.record_type,
                    "min_completeness": args.min_completeness,
                    "max_completeness": args.max_completeness,
                }
            ),
            options_json=json.dumps({"limit": args.limit}),
            total_records=len(records),
            status="pending",
        )
        db.add(campaign)
        await db.flush()

        jobs = 0
        for record in records:
            if not record.source_url:
                continue
            db.add(
                BackfillJob(
                    campaign_id=campaign.id,
                    record_id=record.id,
                    url_to_crawl=record.source_url,
                    before_completeness=record.completeness_score,
                )
            )
            jobs += 1

        await db.commit()
        print(f"Created campaign {campaign.id} with {jobs} jobs")


async def cmd_list(_args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(BackfillCampaign).order_by(BackfillCampaign.created_at.desc()))).scalars().all()
        for row in rows:
            print(
                f"{row.id} {row.status} total={row.total_records} "
                f"processed={row.processed_records} success={row.successful_updates} failed={row.failed_updates}"
            )


async def cmd_status(args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as db:
        campaign = await db.get(BackfillCampaign, args.campaign_id)
        if campaign is None:
            raise SystemExit("Campaign not found")
        print(
            json.dumps(
                {
                    "id": campaign.id,
                    "name": campaign.name,
                    "status": campaign.status,
                    "total_records": campaign.total_records,
                    "processed_records": campaign.processed_records,
                    "successful_updates": campaign.successful_updates,
                    "failed_updates": campaign.failed_updates,
                },
                indent=2,
                default=str,
            )
        )


async def cmd_monitor(args: argparse.Namespace) -> None:
    interval = max(args.interval, 1)
    try:
        while True:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(BackfillCampaign)
                    .where(BackfillCampaign.status == "running")
                    .order_by(BackfillCampaign.started_at.desc())
                )
                campaigns = result.scalars().all()

                print("\033[2J\033[H", end="")
                print("=" * 80)
                print(f"Backfill Campaign Monitor - {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print("=" * 80)
                print()

                if not campaigns:
                    print("No running campaigns.")
                else:
                    for c in campaigns:
                        pct = int((c.processed_records / c.total_records) * 100) if c.total_records > 0 else 0
                        bar_length = 40
                        filled = int(bar_length * pct / 100)
                        bar = "█" * filled + "░" * (bar_length - filled)

                        print(c.name)
                        print(f"  ID: {c.id}")
                        print(f"  Progress: {c.processed_records}/{c.total_records} ({pct}%)")
                        print(f"  Successful: {c.successful_updates} | Failed: {c.failed_updates}")
                        print(f"  [{bar}] {pct}%")
                        print()

                print(f"Refreshing every {interval}s... (Ctrl+C to stop)")
            await asyncio.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


async def cmd_schedule_create(args: argparse.Namespace) -> None:
    if not croniter.is_valid(args.cron):
        raise SystemExit("Invalid cron expression")

    filters = {
        "record_type": args.record_type,
        "min_completeness": args.min_completeness,
        "max_completeness": args.max_completeness,
    }
    options = {"limit": args.limit}
    next_run = croniter(args.cron, datetime.now(UTC)).get_next(datetime)

    async with AsyncSessionLocal() as db:
        schedule = BackfillSchedule(
            name=args.name,
            schedule_type="recurring",
            cron_expression=args.cron,
            filters_json=json.dumps(filters),
            options_json=json.dumps(options),
            auto_start=args.auto_start,
            enabled=not args.disabled,
            next_run_at=next_run,
        )
        db.add(schedule)
        await db.commit()

        print(f"Created schedule {schedule.id}")
        print(f"Next run: {next_run}")


async def cmd_schedule_list(_args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(select(BackfillSchedule).order_by(BackfillSchedule.next_run_at.asc().nullslast()))
        ).scalars().all()
        if not rows:
            print("No schedules found")
            return

        for row in rows:
            status = "enabled" if row.enabled else "disabled"
            print(
                f"{row.id} {status} auto_start={row.auto_start} "
                f"cron={row.cron_expression} next_run={row.next_run_at} name={row.name}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill campaign commands")
    sub = parser.add_subparsers(dest="command", required=True)

    incomplete = sub.add_parser("incomplete", help="Create/list incomplete-record campaign")
    incomplete.add_argument("--record-type", default="artist")
    incomplete.add_argument("--min-completeness", type=int, default=0)
    incomplete.add_argument("--max-completeness", type=int, default=70)
    incomplete.add_argument("--limit", type=int, default=100)
    incomplete.add_argument("--name", default="Backfill Incomplete Records")
    incomplete.add_argument("--dry-run", action="store_true")

    sub.add_parser("list", help="List campaigns")

    status = sub.add_parser("status", help="Campaign status")
    status.add_argument("campaign_id")

    monitor = sub.add_parser("monitor", help="Monitor running campaigns")
    monitor.add_argument("--interval", type=int, default=5)

    schedule_create = sub.add_parser("schedule-create", help="Create recurring schedule")
    schedule_create.add_argument("--name", required=True)
    schedule_create.add_argument("--cron", required=True, help="Cron expression")
    schedule_create.add_argument("--record-type", default="artist")
    schedule_create.add_argument("--min-completeness", type=int, default=0)
    schedule_create.add_argument("--max-completeness", type=int, default=70)
    schedule_create.add_argument("--limit", type=int, default=100)
    schedule_create.add_argument("--auto-start", action="store_true")
    schedule_create.add_argument("--disabled", action="store_true")

    sub.add_parser("schedule-list", help="List schedules")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "incomplete":
        asyncio.run(cmd_incomplete(args))
    elif args.command == "list":
        asyncio.run(cmd_list(args))
    elif args.command == "status":
        asyncio.run(cmd_status(args))
    elif args.command == "monitor":
        asyncio.run(cmd_monitor(args))
    elif args.command == "schedule-create":
        asyncio.run(cmd_schedule_create(args))
    elif args.command == "schedule-list":
        asyncio.run(cmd_schedule_list(args))


if __name__ == "__main__":
    main()
