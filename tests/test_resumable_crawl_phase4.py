import pytest

from app.crawler.durable_frontier import run_durable_crawl
from app.crawler.resume_service import resume_crawl_run
from app.db import crud


@pytest.mark.asyncio
async def test_checkpoint_upsert_and_update(db_session):
    source = await crud.create_source(db_session, url="https://checkpoint.test")
    run = await crud.create_crawl_run(
        db_session,
        source_id=source.id,
        seed_url=source.url,
        status="running",
        mapping_version_id="map-v1",
    )

    checkpoint = await crud.upsert_crawl_run_checkpoint(
        db_session,
        crawl_run_id=run.id,
        source_id=source.id,
        mapping_version_id="map-v1",
        status="running",
        frontier_counts={"queued": 2},
        last_processed_url="https://checkpoint.test/a",
        progress={"processed": 1},
        worker_state={"worker_id": "w1"},
    )
    assert checkpoint.crawl_run_id == run.id

    updated = await crud.upsert_crawl_run_checkpoint(
        db_session,
        crawl_run_id=run.id,
        source_id=source.id,
        mapping_version_id="map-v1",
        status="paused",
        frontier_counts={"queued": 1, "fetched": 1},
        last_processed_url="https://checkpoint.test/b",
    )
    assert updated.id == checkpoint.id
    assert updated.status == "paused"


@pytest.mark.asyncio
async def test_resume_service_requeues_retryable_and_keeps_mapping_version(db_session):
    source = await crud.create_source(db_session, url="https://resume.test")
    run = await crud.create_crawl_run(
        db_session,
        source_id=source.id,
        seed_url=source.url,
        status="paused",
        mapping_version_id="map-approved-v2",
    )
    await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=run.id,
        source_id=source.id,
        rows=[
            {
                "url": "https://resume.test/a",
                "normalized_url": "https://resume.test/a",
                "depth": 0,
                "status": "failed_retryable",
                "mapping_version_id": "map-approved-v2",
            },
            {
                "url": "https://resume.test/b",
                "normalized_url": "https://resume.test/b",
                "depth": 0,
                "status": "extracted",
                "mapping_version_id": "map-approved-v2",
            },
        ],
    )

    result = await resume_crawl_run(db_session, crawl_run_id=run.id)
    assert result["status"] == "running"
    assert result["mapping_version_id"] == "map-approved-v2"

    counts = await crud.get_crawl_frontier_counts(db_session, run.id)
    assert counts.get("queued", 0) == 1
    assert counts.get("extracted", 0) == 1


@pytest.mark.asyncio
async def test_resume_api_returns_frontier_summary(test_client, db_session):
    source = await crud.create_source(db_session, url="https://resume-api.test")
    run = await crud.create_crawl_run(
        db_session,
        source_id=source.id,
        seed_url=source.url,
        status="paused",
        mapping_version_id="map-approved-v3",
    )
    await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=run.id,
        source_id=source.id,
        rows=[
            {
                "url": "https://resume-api.test/retry",
                "normalized_url": "https://resume-api.test/retry",
                "depth": 1,
                "status": "failed_retryable",
                "mapping_version_id": "map-approved-v3",
                "last_error": "timeout",
            }
        ],
    )

    resume_resp = await test_client.post(f"/api/crawl-runs/{run.id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["mapping_version_id"] == "map-approved-v3"

    detail_resp = await test_client.get(f"/api/crawl-runs/{run.id}")
    assert detail_resp.status_code == 200
    payload = detail_resp.json()
    assert payload["mapping_version_id"] == "map-approved-v3"
    assert payload["resumable"] is True


@pytest.mark.asyncio
async def test_durable_frontier_populated_with_mapping_attribution(db_session, monkeypatch):
    source = await crud.create_source(db_session, url="https://frontier-map.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    await crud.update_source(db_session, source.id, published_mapping_version_id=mapping.id)

    class _FetchResult:
        def __init__(self):
            self.status_code = 200
            self.error = None
            self.final_url = "https://frontier-map.test"
            self.method = "httpx"
            self.html = "<html><body><a href='/artists'>Artists</a></body></html>"

    class _Robots:
        async def is_allowed(self, _url: str) -> bool:
            return True

    async def _fake_fetch(_url: str):
        return _FetchResult()

    monkeypatch.setattr("app.crawler.durable_frontier.fetch", _fake_fetch)
    await run_durable_crawl(
        db_session,
        source_id=source.id,
        seed_url=source.url,
        job_id=None,
        worker_id="worker-phase4",
        max_pages=1,
        max_depth=2,
        robots_checker=_Robots(),
    )
    crawl_run = await crud.get_active_crawl_run_for_source(db_session, source.id)
    assert crawl_run is not None
    assert crawl_run.mapping_version_id == mapping.id
    frontier = await crud.get_crawl_frontier_counts(db_session, crawl_run.id)
    assert frontier.get("fetched", 0) >= 1
