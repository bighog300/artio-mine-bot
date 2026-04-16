from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import BackfillCampaign, BackfillJob
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

    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "incomplete":
        asyncio.run(cmd_incomplete(args))
    elif args.command == "list":
        asyncio.run(cmd_list(args))
    elif args.command == "status":
        asyncio.run(cmd_status(args))


if __name__ == "__main__":
    main()
