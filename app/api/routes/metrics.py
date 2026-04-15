from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db import crud
from app.db.models import Page, Record
from app.metrics import metrics as runtime_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    total_artists = (
        await db.execute(select(func.count(Record.id)).where(Record.record_type == "artist"))
    ).scalar_one()
    avg_completeness = (
        await db.execute(select(func.avg(Record.completeness_score)).where(Record.record_type == "artist"))
    ).scalar_one()
    conflicts_count = (
        await db.execute(select(func.count(Record.id)).where(Record.has_conflicts.is_(True)))
    ).scalar_one()
    records_enriched = (
        await db.execute(select(func.count(Record.id)).where(Record.completeness_score > 0))
    ).scalar_one()
    pages_processed = (await db.execute(select(func.count(Page.id)))).scalar_one()
    duplicates_detected = await crud.count_duplicate_reviews(db)
    merges_performed = await crud.count_audit_actions(db, action_type="merge")

    runtime_snapshot = runtime_metrics.snapshot()

    return {
        "total_artists": total_artists,
        "avg_completeness": round(float(avg_completeness or 0), 2),
        "conflicts_count": conflicts_count,
        "records_enriched": records_enriched,
        "pages_processed": pages_processed,
        "duplicates_detected": duplicates_detected,
        "merges_performed": merges_performed,
        "runtime": runtime_snapshot,
    }
