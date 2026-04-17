from datetime import UTC, datetime, timedelta

import pytest

from app.db import crud


@pytest.mark.asyncio
async def test_create_crawl_run_and_frontier_dedupe(db_session):
    source = await crud.create_source(db_session, url="https://crawl-state.test")
    crawl_run = await crud.create_crawl_run(
        db_session,
        source_id=source.id,
        seed_url=source.url,
        status="running",
    )

    inserted = await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=crawl_run.id,
        source_id=source.id,
        rows=[
            {"url": "https://crawl-state.test/a", "normalized_url": "https://crawl-state.test/a", "depth": 0},
            {"url": "https://crawl-state.test/a#fragment", "normalized_url": "https://crawl-state.test/a", "depth": 0},
        ],
    )
    assert inserted == 1


@pytest.mark.asyncio
async def test_claim_and_reclaim_expired_leases(db_session):
    source = await crud.create_source(db_session, url="https://leases.test")
    crawl_run = await crud.create_crawl_run(db_session, source_id=source.id, seed_url=source.url, status="running")
    await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=crawl_run.id,
        source_id=source.id,
        rows=[{"url": f"https://leases.test/{i}", "normalized_url": f"https://leases.test/{i}", "depth": 0} for i in range(3)],
    )

    claimed = await crud.claim_frontier_rows(db_session, crawl_run_id=crawl_run.id, worker_id="worker-a", limit=2, lease_seconds=1)
    assert len(claimed) == 2

    for row in claimed:
        await crud.update_frontier_row(db_session, row.id, lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))

    reclaimed = await crud.reclaim_expired_frontier_leases(db_session, crawl_run_id=crawl_run.id)
    assert reclaimed == 2
