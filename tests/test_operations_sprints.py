import pytest
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import logs as logs_routes
from app.db import crud


@pytest.mark.asyncio
async def test_source_actions_and_retry_failed(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://ops-source.example")

    start_discovery = await test_client.post(f"/api/sources/{source.id}/actions/start-discovery")
    assert start_discovery.status_code == 200
    assert start_discovery.json()["status"] == "running"

    pause = await test_client.post(f"/api/sources/{source.id}/actions/pause")
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"

    stop = await test_client.post(f"/api/sources/{source.id}/actions/stop")
    assert stop.status_code == 200
    assert stop.json()["status"] == "idle"

    failed_job = await crud.create_job(db_session, source_id=source.id, job_type="extract_page", payload={})
    await crud.update_job_status(db_session, failed_job.id, "failed", error_message="boom")

    retry = await test_client.post(f"/api/sources/{source.id}/actions/retry-failed")
    assert retry.status_code == 200
    assert retry.json()["queued_jobs"] >= 1


@pytest.mark.asyncio
async def test_jobs_pause_resume_and_cancel(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://jobs-pause.example")
    job = await crud.create_job(db_session, source_id=source.id, job_type="crawl_section", payload={})

    pause_resp = await test_client.post(f"/api/jobs/{job.id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    resume_resp = await test_client.post(f"/api/jobs/{job.id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "pending"

    cancel_resp = await test_client.post(f"/api/jobs/{job.id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_queues_summary_pause_and_resume(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://queue-source.example")
    await crud.create_job(db_session, source_id=source.id, job_type="crawl_section", payload={})

    queues = await test_client.get("/api/queues")
    assert queues.status_code == 200
    assert queues.json()["total"] == 1
    assert "pending" in queues.json()["items"][0]

    pause_resp = await test_client.post("/api/queues/default/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    resume_resp = await test_client.post("/api/queues/default/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "running"


@pytest.mark.asyncio
async def test_activity_logs_endpoint(test_client: AsyncClient):
    response = await test_client.get("/api/logs/activity")
    assert response.status_code == 200
    assert "items" in response.json()


@pytest.mark.asyncio
async def test_activity_logs_endpoint_db_error_fallback(test_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    async def _broken_list_logs(*args, **kwargs):
        raise SQLAlchemyError("logs table missing")

    monkeypatch.setattr(logs_routes, "list_logs", _broken_list_logs)

    response = await test_client.get("/api/logs/activity")
    assert response.status_code == 200
    assert response.json() == {"items": []}


@pytest.mark.asyncio
async def test_activity_logs_endpoint_unexpected_error_fallback(test_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    async def _broken_list_logs(*args, **kwargs):
        raise RuntimeError("unexpected crash")

    monkeypatch.setattr(logs_routes, "list_logs", _broken_list_logs)

    response = await test_client.get("/api/logs/activity")
    assert response.status_code == 200
    assert response.json() == {"items": []}


@pytest.mark.asyncio
async def test_activity_logs_endpoint_handles_non_string_messages(test_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    class _FakeLog:
        id = "log-1"
        timestamp = "2026-01-01T00:00:00Z"
        level = "info"
        service = "api"
        source_id = None
        message = 42
        context = None

    async def _fake_list_logs(*args, **kwargs):
        return ([_FakeLog()], 1)

    monkeypatch.setattr(logs_routes, "list_logs", _fake_list_logs)

    response = await test_client.get("/api/logs/activity")
    assert response.status_code == 200
    assert response.json() == {"items": []}


@pytest.mark.asyncio
async def test_duplicate_reviews_endpoint_db_error_fallback(test_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    async def _broken_list_duplicate_reviews(*args, **kwargs):
        raise SQLAlchemyError("duplicate_reviews table missing")

    monkeypatch.setattr(crud, "list_duplicate_reviews", _broken_list_duplicate_reviews)

    response = await test_client.get("/api/duplicates/reviews", params={"status": "pending", "skip": 0, "limit": 20})
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "skip": 0, "limit": 20}


@pytest.mark.asyncio
async def test_duplicate_reviews_endpoint_unexpected_error_fallback(test_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    async def _broken_list_duplicate_reviews(*args, **kwargs):
        raise RuntimeError("unexpected duplicate review failure")

    monkeypatch.setattr(crud, "list_duplicate_reviews", _broken_list_duplicate_reviews)

    response = await test_client.get("/api/duplicates/reviews", params={"status": "pending", "skip": 0, "limit": 20})
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "skip": 0, "limit": 20}


@pytest.mark.asyncio
async def test_duplicate_reviews_endpoint_uses_total_count(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://dup-total.example")
    left = await crud.create_record(db_session, source_id=source.id, record_type="artist", title="Alice")
    middle = await crud.create_record(db_session, source_id=source.id, record_type="artist", title="Alicia")
    right = await crud.create_record(db_session, source_id=source.id, record_type="artist", title="Alise")

    await crud.upsert_duplicate_review(
        db_session,
        left_record_id=left.id,
        right_record_id=middle.id,
        similarity_score=90,
        reason="name similarity",
    )
    await crud.upsert_duplicate_review(
        db_session,
        left_record_id=left.id,
        right_record_id=right.id,
        similarity_score=85,
        reason="embedding similarity",
    )

    response = await test_client.get("/api/duplicates/reviews", params={"status": "pending", "skip": 0, "limit": 1})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["total"] == 2
