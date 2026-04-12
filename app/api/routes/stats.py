from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import GlobalStats, PageStats, RecordStats, SourceStats2
from app.db.models import Page, Record, Source

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=GlobalStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    # Source stats
    total_sources = (await db.execute(select(func.count(Source.id)))).scalar_one()
    active_sources = (
        await db.execute(
            select(func.count(Source.id)).where(
                Source.status.in_(["mapping", "crawling", "extracting"])
            )
        )
    ).scalar_one()
    done_sources = (
        await db.execute(select(func.count(Source.id)).where(Source.status == "done"))
    ).scalar_one()

    # Record stats
    total_records = (await db.execute(select(func.count(Record.id)))).scalar_one()
    pending = (
        await db.execute(select(func.count(Record.id)).where(Record.status == "pending"))
    ).scalar_one()
    approved = (
        await db.execute(select(func.count(Record.id)).where(Record.status == "approved"))
    ).scalar_one()
    rejected = (
        await db.execute(select(func.count(Record.id)).where(Record.status == "rejected"))
    ).scalar_one()
    exported = (
        await db.execute(select(func.count(Record.id)).where(Record.status == "exported"))
    ).scalar_one()

    # By type
    by_type: dict[str, int] = {}
    for rtype in ("artist", "event", "exhibition", "venue", "artwork"):
        count = (
            await db.execute(
                select(func.count(Record.id)).where(Record.record_type == rtype)
            )
        ).scalar_one()
        by_type[rtype] = count

    # By confidence
    by_confidence: dict[str, int] = {}
    for band in ("HIGH", "MEDIUM", "LOW"):
        count = (
            await db.execute(
                select(func.count(Record.id)).where(Record.confidence_band == band)
            )
        ).scalar_one()
        by_confidence[band] = count

    # Page stats
    total_pages = (await db.execute(select(func.count(Page.id)))).scalar_one()
    crawled_pages = (
        await db.execute(
            select(func.count(Page.id)).where(Page.status.in_(["fetched", "classified", "extracted"]))
        )
    ).scalar_one()
    error_pages = (
        await db.execute(select(func.count(Page.id)).where(Page.status == "error"))
    ).scalar_one()

    return GlobalStats(
        sources=SourceStats2(
            total=total_sources,
            active=active_sources,
            done=done_sources,
        ),
        records=RecordStats(
            total=total_records,
            pending=pending,
            approved=approved,
            rejected=rejected,
            exported=exported,
            by_type=by_type,
            by_confidence=by_confidence,
        ),
        pages=PageStats(
            total=total_pages,
            crawled=crawled_pages,
            error=error_pages,
        ),
    )
