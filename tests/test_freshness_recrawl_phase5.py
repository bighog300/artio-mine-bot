from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.crawler.durable_frontier import run_durable_crawl
from app.crawler.freshness import compute_next_eligible_fetch_at, detect_content_change
from app.db import crud


@pytest.mark.parametrize(
    ("policy", "expected_days", "is_none"),
    [
        ("daily", 1, False),
        ("weekly", 7, False),
        ("monthly", 30, False),
        ("manual", 0, True),
    ],
)
def test_freshness_policy_next_eligible(policy: str, expected_days: int, is_none: bool):
    now = datetime(2026, 4, 21, tzinfo=UTC)
    result = compute_next_eligible_fetch_at(policy=policy, now=now)
    if is_none:
        assert result is None
    else:
        assert result == now + timedelta(days=expected_days)


def test_change_detection_precedence():
    changed = detect_content_change(
        previous_content_hash="a",
        new_content_hash="b",
        previous_etag="one",
        new_etag="two",
        previous_last_modified="old",
        new_last_modified="new",
    )
    assert changed.changed is True
    assert changed.reason == "content_hash"

    unchanged = detect_content_change(
        previous_content_hash="a",
        new_content_hash="a",
        previous_etag="one",
        new_etag="one",
        previous_last_modified="old",
        new_last_modified="old",
    )
    assert unchanged.changed is False


@pytest.mark.asyncio
async def test_refresh_selection_only_includes_due_urls(db_session):
    source = await crud.create_source(db_session, url="https://refresh-selection.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    await crud.update_source(
        db_session,
        source.id,
        published_mapping_version_id=mapping.id,
        active_mapping_version_id=mapping.id,
    )
    run = await crud.create_crawl_run(
        db_session,
        source_id=source.id,
        seed_url=source.url,
        status="queued",
        mapping_version_id=mapping.id,
    )
    now = datetime.now(UTC)
    await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=run.id,
        source_id=source.id,
        rows=[
            {
                "url": "https://refresh-selection.test/due",
                "normalized_url": "https://refresh-selection.test/due",
                "status": "extracted",
                "mapping_version_id": mapping.id,
                "next_eligible_fetch_at": now - timedelta(minutes=1),
            },
            {
                "url": "https://refresh-selection.test/not-due",
                "normalized_url": "https://refresh-selection.test/not-due",
                "status": "extracted",
                "mapping_version_id": mapping.id,
                "next_eligible_fetch_at": now + timedelta(days=1),
            },
        ],
    )
    refresh_run = await crud.create_crawl_run(
        db_session,
        source_id=source.id,
        seed_url=source.url,
        status="queued",
        mapping_version_id=mapping.id,
    )
    selection = await crud.prepare_refresh_frontier_rows(
        db_session,
        crawl_run_id=refresh_run.id,
        source_id=source.id,
        mapping_version_id=mapping.id,
        force=False,
    )
    assert selection["selected"] == 1
    assert selection["skipped_not_due"] == 1


@pytest.mark.asyncio
async def test_refresh_unchanged_skips_downstream_reextract(db_session, monkeypatch):
    source = await crud.create_source(db_session, url="https://refresh-unchanged.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    mapping.status = "approved"
    mapping.mapping_json = '{"family_rules":[{"family_key":"root","freshness_policy":"daily"}]}'
    await db_session.commit()
    await crud.update_source(db_session, source.id, published_mapping_version_id=mapping.id)
    run = await crud.create_crawl_run(db_session, source_id=source.id, seed_url=source.url, status="queued", mapping_version_id=mapping.id)
    await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=run.id,
        source_id=source.id,
        rows=[{
            "url": source.url,
            "normalized_url": source.url,
            "mapping_version_id": mapping.id,
            "family_key": "root",
            "status": "queued",
            "content_hash": "hash-same",
            "next_eligible_fetch_at": datetime.now(UTC) - timedelta(minutes=1),
        }],
    )
    frontier = (await crud.claim_frontier_rows(db_session, crawl_run_id=run.id, worker_id="prep", limit=1))[0]
    await crud.update_frontier_row(db_session, frontier.id, status="queued", lease_expires_at=None, leased_by_worker=None, last_fetched_at=datetime.now(UTC))

    async def _fake_fetch(_url: str):
        return SimpleNamespace(
            status_code=200,
            error=None,
            final_url=source.url,
            method="httpx",
            html="same",
            etag=None,
            last_modified=None,
        )

    monkeypatch.setattr("app.crawler.durable_frontier.fetch", _fake_fetch)
    monkeypatch.setattr("app.crawler.durable_frontier.hashlib.sha256", lambda _b: SimpleNamespace(hexdigest=lambda: "hash-same"))
    result = await run_durable_crawl(
        db_session,
        source_id=source.id,
        seed_url=source.url,
        job_id=None,
        worker_id="worker-refresh",
        max_pages=1,
        max_depth=1,
        refresh_mode=True,
        crawl_run_id=run.id,
    )
    assert result["unchanged"] >= 1
    fetched_pages = await crud.list_pages_by_statuses(db_session, source_id=source.id, statuses=["fetched"], limit=10)
    assert fetched_pages == []


@pytest.mark.asyncio
async def test_refresh_changed_marks_for_downstream_work(db_session, monkeypatch):
    source = await crud.create_source(db_session, url="https://refresh-changed.test")
    mapping = await crud.create_source_mapping_version(db_session, source.id)
    mapping.status = "approved"
    mapping.mapping_json = '{"family_rules":[{"family_key":"root","freshness_policy":"daily"}]}'
    await db_session.commit()
    await crud.update_source(db_session, source.id, published_mapping_version_id=mapping.id)
    run = await crud.create_crawl_run(db_session, source_id=source.id, seed_url=source.url, status="queued", mapping_version_id=mapping.id)
    page, _ = await crud.get_or_create_page(db_session, source_id=source.id, url=source.url)
    await crud.update_page(db_session, page.id, status="extracted", html="old")
    await crud.upsert_crawl_frontier_rows(
        db_session,
        crawl_run_id=run.id,
        source_id=source.id,
        rows=[{
            "url": source.url,
            "normalized_url": source.url,
            "mapping_version_id": mapping.id,
            "family_key": "root",
            "status": "queued",
            "content_hash": "old-hash",
            "last_fetched_at": datetime.now(UTC) - timedelta(days=1),
            "next_eligible_fetch_at": datetime.now(UTC) - timedelta(minutes=1),
        }],
    )

    async def _fake_fetch(_url: str):
        return SimpleNamespace(
            status_code=200,
            error=None,
            final_url=source.url,
            method="httpx",
            html="new html",
            etag="etag-2",
            last_modified="Wed, 21 Apr 2026 00:00:00 GMT",
        )

    monkeypatch.setattr("app.crawler.durable_frontier.fetch", _fake_fetch)
    monkeypatch.setattr("app.crawler.durable_frontier._extract_links", lambda *_args, **_kwargs: [])
    result = await run_durable_crawl(
        db_session,
        source_id=source.id,
        seed_url=source.url,
        job_id=None,
        worker_id="worker-refresh",
        max_pages=1,
        max_depth=1,
        refresh_mode=True,
        crawl_run_id=run.id,
    )
    assert result["changed"] >= 1
    updated_page = await crud.get_page(db_session, page.id)
    assert updated_page is not None
    assert updated_page.status == "fetched"


@pytest.mark.asyncio
async def test_refresh_api_trigger_and_eligibility(test_client, monkeypatch):
    class _FakeQueue:
        def enqueue(self, *_args, **_kwargs):
            return SimpleNamespace(id="rq-refresh")

    monkeypatch.setattr("app.api.routes.source_mappings.get_default_queue", lambda: _FakeQueue())
    source_resp = await test_client.post("/api/sources", json={"url": "https://refresh-api.test"})
    source_id = source_resp.json()["id"]
    profile_resp = await test_client.post(f"/api/sources/{source_id}/profiles", json={"max_pages": 20})
    draft_resp = await test_client.post(f"/api/sources/{source_id}/mappings/draft", json={"profile_id": profile_resp.json()["id"]})
    mapping_id = draft_resp.json()["id"]
    await test_client.post(f"/api/sources/{source_id}/mappings/{mapping_id}/approve")

    eligibility = await test_client.get(f"/api/sources/{source_id}/mappings/{mapping_id}/refresh/eligibility")
    assert eligibility.status_code == 200
    assert "eligible" in eligibility.json()

    trigger = await test_client.post(f"/api/sources/{source_id}/mappings/{mapping_id}/refresh")
    assert trigger.status_code == 200
    assert trigger.json()["queue_job_id"] == "rq-refresh"
