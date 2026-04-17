import pytest

from app.db import crud


@pytest.mark.asyncio
async def test_crawl_run_progress_endpoint(test_client, db_session):
    source = await crud.create_source(db_session, url="https://progress.test")
    crawl_run = await crud.create_crawl_run(
        db_session,
        source_id=source.id,
        seed_url=source.url,
        status="running",
    )
    await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=crawl_run.id,
        source_id=source.id,
        rows=[
            {"url": "https://progress.test/a", "normalized_url": "https://progress.test/a", "depth": 0, "status": "queued"},
            {"url": "https://progress.test/b", "normalized_url": "https://progress.test/b", "depth": 0, "status": "queued"},
        ],
    )

    resp = await test_client.get(f"/api/crawl-runs/{crawl_run.id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["crawl_run_id"] == crawl_run.id
    assert payload["queued_count"] >= 2
