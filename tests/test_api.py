import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud


@pytest.mark.asyncio
async def test_health_endpoint(test_client: AsyncClient):
    resp = await test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "db" in data


@pytest.mark.asyncio
async def test_create_source(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/sources", json={"url": "https://testsite.com", "name": "Test Site"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://testsite.com"
    assert data["name"] == "Test Site"
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_source_duplicate(test_client: AsyncClient):
    await test_client.post("/api/sources", json={"url": "https://dup.com"})
    resp = await test_client.post("/api/sources", json={"url": "https://dup.com"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_sources(test_client: AsyncClient):
    await test_client.post("/api/sources", json={"url": "https://list1.com"})
    await test_client.post("/api/sources", json={"url": "https://list2.com"})
    resp = await test_client.get("/api/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_get_source(test_client: AsyncClient):
    create_resp = await test_client.post("/api/sources", json={"url": "https://get1.com"})
    source_id = create_resp.json()["id"]
    resp = await test_client.get(f"/api/sources/{source_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == source_id


@pytest.mark.asyncio
async def test_get_source_not_found(test_client: AsyncClient):
    resp = await test_client.get("/api/sources/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_source(test_client: AsyncClient):
    create_resp = await test_client.post("/api/sources", json={"url": "https://del1.com"})
    source_id = create_resp.json()["id"]
    resp = await test_client.delete(f"/api/sources/{source_id}")
    assert resp.status_code == 204
    get_resp = await test_client.get(f"/api/sources/{source_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_stats(test_client: AsyncClient):
    resp = await test_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert "records" in data
    assert "pages" in data
    assert "total" in data["sources"]
    assert "by_type" in data["records"]


@pytest.mark.asyncio
async def test_list_records(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://records-test.com")
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Test Artist",
        confidence_score=80,
        confidence_band="HIGH",
    )
    await db_session.commit()

    resp = await test_client.get("/api/records")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_approve_record(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://approve-test.com")
    record = await crud.create_record(
        db_session, source_id=source.id, record_type="artist", title="Artist to Approve"
    )
    await db_session.commit()

    resp = await test_client.post(f"/api/records/{record.id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_record(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://reject-test.com")
    record = await crud.create_record(
        db_session, source_id=source.id, record_type="artist", title="Artist to Reject"
    )
    await db_session.commit()

    resp = await test_client.post(
        f"/api/records/{record.id}/reject", json={"reason": "Not relevant"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_bulk_approve(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://bulk-test.com")
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="High Confidence",
        confidence_score=85,
        confidence_band="HIGH",
    )
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Low Confidence",
        confidence_score=20,
        confidence_band="LOW",
    )
    await db_session.commit()

    resp = await test_client.post(
        "/api/records/bulk-approve",
        json={"source_id": source.id, "min_confidence": 70},
    )
    assert resp.status_code == 200
    assert resp.json()["approved_count"] == 1


@pytest.mark.asyncio
async def test_list_pages(test_client: AsyncClient):
    resp = await test_client.get("/api/pages")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data




def test_enqueue_pipeline_job_passes_job_id_as_function_argument():
    from app.api.routes import mine

    captured: dict[str, object] = {}

    class _FakeQueue:
        def enqueue(self, func_name: str, *args, **kwargs):
            captured["func_name"] = func_name
            captured["args"] = args
            captured["kwargs"] = kwargs
            return SimpleNamespace(id="rq-id-123")

    with patch("app.api.routes.mine.get_default_queue", return_value=_FakeQueue()):
        rq_job_id = mine._enqueue_pipeline_job("db-job-id", "source-1", "run_full_pipeline", {"k": "v"})

    assert rq_job_id == "rq-id-123"
    assert captured["func_name"] == "app.pipeline.runner.process_pipeline_job"
    assert captured["args"] == ("db-job-id", "source-1", "run_full_pipeline", {"k": "v"})
    assert captured["kwargs"] == {"job_timeout": mine.PIPELINE_JOB_TIMEOUT_SECONDS}

@pytest.mark.asyncio
async def test_mine_start(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/sources", json={"url": "https://mine-test.com"}
    )
    source_id = create_resp.json()["id"]

    with patch(
        "app.api.routes.mine._enqueue_pipeline_job",
        return_value="mock-rq-job-id",
    ):
        resp = await test_client.post(f"/api/mine/{source_id}/start")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("queued", "running", "pending")


@pytest.mark.asyncio
async def test_mine_start_sets_source_queued(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/sources", json={"url": "https://mine-queued.com"}
    )
    source_id = create_resp.json()["id"]

    with patch(
        "app.api.routes.mine._enqueue_pipeline_job",
        return_value="mock-rq-job-id",
    ):
        resp = await test_client.post(f"/api/mine/{source_id}/start")

    assert resp.status_code == 200
    source_resp = await test_client.get(f"/api/sources/{source_id}")
    assert source_resp.status_code == 200
    assert source_resp.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_mine_resume_chooses_extract_when_pages_pending_extraction(
    test_client: AsyncClient, db_session: AsyncSession
):
    source = await crud.create_source(
        db_session, url="https://resume-extract.com", name="Resume Extract"
    )
    await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://resume-extract.com/page-1",
        original_url="https://resume-extract.com/page-1",
        status="fetched",
    )

    with patch("app.api.routes.mine._enqueue_pipeline_job", return_value="rq-resume-extract"):
        resp = await test_client.post(f"/api/mine/{source.id}/resume")

    assert resp.status_code == 202
    assert "extract_page" in resp.json()["message"]


@pytest.mark.asyncio
async def test_mine_resume_chooses_crawl_for_paused_source_with_site_map(
    test_client: AsyncClient, db_session: AsyncSession
):
    source = await crud.create_source(db_session, url="https://resume-crawl.com")
    await crud.update_source(
        db_session,
        source.id,
        status="paused",
        site_map=json.dumps({"root_url": source.url, "sections": []}),
    )

    with patch("app.api.routes.mine._enqueue_pipeline_job", return_value="rq-resume-crawl"):
        resp = await test_client.post(f"/api/mine/{source.id}/resume")

    assert resp.status_code == 202
    assert "crawl_section" in resp.json()["message"]


@pytest.mark.asyncio
async def test_mining_status_includes_queued_job(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/sources", json={"url": "https://mine-status-queued.com"}
    )
    source_id = create_resp.json()["id"]

    with patch(
        "app.api.routes.mine._enqueue_pipeline_job",
        return_value="mock-rq-job-id",
    ):
        await test_client.post(f"/api/mine/{source_id}/start")

    status_resp = await test_client.get(f"/api/mine/{source_id}/status")
    assert status_resp.status_code == 200
    payload = status_resp.json()
    assert payload["status"] == "queued"
    assert payload["current_job"] is not None
    assert payload["current_job"]["status"] == "queued"


@pytest.mark.asyncio
async def test_mine_start_not_found(test_client: AsyncClient):
    resp = await test_client.post("/api/mine/nonexistent/start")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mine_start_returns_controlled_error_when_enqueue_fails(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/sources", json={"url": "https://mine-enqueue-fail.com"}
    )
    source_id = create_resp.json()["id"]

    with (
        patch("app.api.routes.mine._assert_queue_available"),
        patch("app.api.routes.mine._enqueue_pipeline_job", side_effect=RuntimeError("redis down")),
    ):
        resp = await test_client.post(f"/api/mine/{source_id}/start")

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Failed to start mining: queue infrastructure unavailable."

    source_resp = await test_client.get(f"/api/sources/{source_id}")
    assert source_resp.status_code == 200
    assert source_resp.json()["status"] == "error"


@pytest.mark.asyncio
async def test_queue_health_endpoint(test_client: AsyncClient):
    with patch(
        "app.api.routes.mine.check_queue_health",
        return_value=SimpleNamespace(redis_ok=True, workers_available=True, worker_count=1),
    ):
        resp = await test_client.get("/api/mine/queue/health")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["redis_ok"] is True
    assert payload["workers_available"] is True
    assert payload["worker_count"] == 1


@pytest.mark.asyncio
async def test_export_preview(test_client: AsyncClient):
    resp = await test_client.get("/api/export/preview")
    assert resp.status_code == 200
    data = resp.json()
    assert "record_count" in data
    assert "artio_configured" in data
    assert "by_type" in data


@pytest.mark.asyncio
async def test_list_images(test_client: AsyncClient):
    resp = await test_client.get("/api/images")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_settings_openai_api_key_flow(test_client: AsyncClient):
    read_resp = await test_client.get("/api/settings")
    assert read_resp.status_code == 200
    assert "openai_api_key_masked" in read_resp.json()
    assert "openai_configured" in read_resp.json()

    save_resp = await test_client.post(
        "/api/settings",
        json={"openai_api_key": "sk-test-openai-1234"},
    )
    assert save_resp.status_code == 200
    payload = save_resp.json()
    assert payload["openai_configured"] is True
    assert payload["openai_api_key_masked"] == "***...1234"


@pytest.mark.asyncio
async def test_settings_save_returns_handled_error_when_env_persist_fails(test_client: AsyncClient):
    with (
        patch("app.api.routes.settings._is_readonly", return_value=False),
        patch("app.api.routes.settings._validate_env_target"),
        patch("dotenv.set_key", side_effect=PermissionError("read-only filesystem")),
    ):
        save_resp = await test_client.post(
            "/api/settings",
            json={"openai_api_key": "sk-test-openai-9999"},
        )

    assert save_resp.status_code == 500
    payload = save_resp.json()
    assert payload["detail"] == "Failed to persist settings to .env. Check file path and permissions."
