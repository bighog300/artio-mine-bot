import json
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
async def test_mine_start_not_found(test_client: AsyncClient):
    resp = await test_client.post("/api/mine/nonexistent/start")
    assert resp.status_code == 404


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
