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
            {"url": "https://crawl-state.test/a", "normalized_url": "https://crawl-state.test/a", "depth": 0, "mapping_version_id": "v1"},
            {"url": "https://crawl-state.test/a#fragment", "normalized_url": "https://crawl-state.test/a", "depth": 0, "mapping_version_id": "v1"},
        ],
    )
    assert inserted == 1

    inserted_other_version = await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=crawl_run.id,
        source_id=source.id,
        rows=[
            {"url": "https://crawl-state.test/a", "normalized_url": "https://crawl-state.test/a", "depth": 0, "mapping_version_id": "v2"},
        ],
    )
    assert inserted_other_version == 1


@pytest.mark.asyncio
async def test_claim_and_reclaim_expired_leases(db_session):
    source = await crud.create_source(db_session, url="https://leases.test")
    crawl_run = await crud.create_crawl_run(db_session, source_id=source.id, seed_url=source.url, status="running")
    await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=crawl_run.id,
        source_id=source.id,
        rows=[{"url": f"https://leases.test/{i}", "normalized_url": f"https://leases.test/{i}", "depth": 0, "status": "queued"} for i in range(3)],
    )

    claimed = await crud.claim_frontier_rows(db_session, crawl_run_id=crawl_run.id, worker_id="worker-a", limit=2, lease_seconds=1)
    assert len(claimed) == 2

    for row in claimed:
        await crud.update_frontier_row(db_session, row.id, lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))

    reclaimed = await crud.reclaim_expired_frontier_leases(db_session, crawl_run_id=crawl_run.id)
    assert reclaimed == 2
    counts = await crud.get_crawl_frontier_counts(db_session, crawl_run.id)
    assert counts.get("failed_retryable", 0) == 2


@pytest.mark.asyncio
async def test_claim_frontier_prefers_priority_then_depth_then_age(db_session):
    source = await crud.create_source(db_session, url="https://priority-order.test")
    crawl_run = await crud.create_crawl_run(db_session, source_id=source.id, seed_url=source.url, status="running")
    await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=crawl_run.id,
        source_id=source.id,
        rows=[
            {
                "url": "https://priority-order.test/utility",
                "normalized_url": "https://priority-order.test/utility",
                "depth": 0,
                "priority": 5,
                "predicted_page_type": "utility",
                "status": "queued",
            },
            {
                "url": "https://priority-order.test/artist/a",
                "normalized_url": "https://priority-order.test/artist/a",
                "depth": 1,
                "priority": 80,
                "predicted_page_type": "artist_profile",
                "status": "queued",
            },
            {
                "url": "https://priority-order.test/artist/b",
                "normalized_url": "https://priority-order.test/artist/b",
                "depth": 0,
                "priority": 80,
                "predicted_page_type": "artist_profile",
                "status": "queued",
            },
        ],
    )

    claimed = await crud.claim_frontier_rows(
        db_session,
        crawl_run_id=crawl_run.id,
        worker_id="worker-priority",
        limit=3,
        lease_seconds=30,
    )
    claimed_urls = [row.url for row in claimed]
    assert claimed_urls == [
        "https://priority-order.test/artist/b",
        "https://priority-order.test/artist/a",
        "https://priority-order.test/utility",
    ]


@pytest.mark.asyncio
async def test_frontier_status_transition_validation(db_session):
    source = await crud.create_source(db_session, url="https://status-transition.test")
    crawl_run = await crud.create_crawl_run(db_session, source_id=source.id, seed_url=source.url, status="running")
    await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=crawl_run.id,
        source_id=source.id,
        rows=[{"url": "https://status-transition.test/a", "normalized_url": "https://status-transition.test/a", "depth": 0, "status": "queued"}],
    )
    claimed = await crud.claim_frontier_rows(db_session, crawl_run_id=crawl_run.id, worker_id="w", limit=1)
    row = claimed[0]
    updated = await crud.update_frontier_row(db_session, row.id, status="fetched")
    assert updated.status == "fetched"
    with pytest.raises(ValueError):
        await crud.update_frontier_row(db_session, row.id, status="queued")
