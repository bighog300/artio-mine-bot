"""Query builder for finding records that need backfilling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Page, Record


class BackfillQuery:
    """Build queries to find records needing backfill."""

    @staticmethod
    async def find_incomplete_records(
        db: AsyncSession,
        record_type: str | None = None,
        min_completeness: int = 0,
        max_completeness: int = 100,
        missing_fields: list[str] | None = None,
        source_ids: list[str] | None = None,
        limit: int = 100,
    ) -> list[Record]:
        stmt = select(Record).where(
            and_(
                Record.completeness_score >= min_completeness,
                Record.completeness_score <= max_completeness,
                Record.status.in_(["pending", "approved"]),
                Record.source_url.is_not(None),
                Record.source_url != "",
            )
        )

        if record_type:
            stmt = stmt.where(Record.record_type == record_type)
        if source_ids:
            stmt = stmt.where(Record.source_id.in_(source_ids))

        # filtering by missing fields requires completeness_details JSON,
        # filter in memory for sqlite compatibility.
        records = list((await db.execute(stmt.order_by(Record.completeness_score.asc()).limit(limit * 4))).scalars().all())
        if missing_fields:
            filtered: list[Record] = []
            for record in records:
                details = getattr(record, "completeness_details", None)
                if not details:
                    continue
                if all(field in details for field in missing_fields):
                    filtered.append(record)
            records = filtered

        return records[:limit]

    @staticmethod
    async def find_uncrawled_urls(
        db: AsyncSession,
        record_type: str | None = None,
        source_ids: list[str] | None = None,
        limit: int = 100,
    ) -> list[Record]:
        stmt = select(Record).where(
            and_(
                Record.source_url.is_not(None),
                Record.source_url != "",
                Record.status.in_(["pending", "approved"]),
            )
        )

        if record_type:
            stmt = stmt.where(Record.record_type == record_type)
        if source_ids:
            stmt = stmt.where(Record.source_id.in_(source_ids))

        stmt = stmt.outerjoin(Page, Page.url == Record.source_url).where(Page.id.is_(None)).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def find_stale_records(
        db: AsyncSession,
        record_type: str | None = None,
        older_than_days: int = 30,
        source_ids: list[str] | None = None,
        limit: int = 100,
    ) -> list[Record]:
        cutoff_date = datetime.now(UTC) - timedelta(days=older_than_days)

        stmt = select(Record).where(
            and_(
                Record.updated_at < cutoff_date,
                Record.status.in_(["pending", "approved"]),
                Record.source_url.is_not(None),
                Record.source_url != "",
            )
        )

        if record_type:
            stmt = stmt.where(Record.record_type == record_type)
        if source_ids:
            stmt = stmt.where(Record.source_id.in_(source_ids))

        result = await db.execute(stmt.order_by(Record.updated_at.asc()).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def find_records_by_source(
        db: AsyncSession,
        source_id: str,
        record_type: str | None = None,
        limit: int = 1000,
    ) -> list[Record]:
        stmt = select(Record).where(
            and_(
                Record.source_id == source_id,
                Record.status.in_(["pending", "approved"]),
                Record.source_url.is_not(None),
                Record.source_url != "",
            )
        )

        if record_type:
            stmt = stmt.where(Record.record_type == record_type)

        result = await db.execute(stmt.limit(limit))
        return list(result.scalars().all())
