import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud


@pytest.mark.asyncio
async def test_api_key_lifecycle(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/keys",
        json={"name": "tenant-a-key", "tenant_id": "tenant-a", "permissions": ["read"]},
    )
    assert create_resp.status_code == 201
    payload = create_resp.json()
    assert payload["raw_key"].startswith("ak_live_")

    list_resp = await test_client.get("/api/keys", params={"tenant_id": "tenant-a"})
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    key_id = list_resp.json()["items"][0]["id"]
    delete_resp = await test_client.delete(f"/api/keys/{key_id}", headers={"X-Tenant-ID": "tenant-a"})
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_v1_requires_api_key(test_client: AsyncClient):
    resp = await test_client.get("/v1/search")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_v1_is_tenant_isolated(test_client: AsyncClient, db_session: AsyncSession):
    source_a = await crud.create_source(db_session, url="https://tenant-a.example", tenant_id="tenant-a")
    source_b = await crud.create_source(db_session, url="https://tenant-b.example", tenant_id="tenant-b")

    await crud.create_record(
        db_session,
        source_id=source_a.id,
        record_type="artist",
        title="Alice Tenant A",
    )
    await crud.create_record(
        db_session,
        source_id=source_b.id,
        record_type="artist",
        title="Bob Tenant B",
    )

    key_resp = await test_client.post(
        "/api/keys",
        json={"name": "tenant-a-public", "tenant_id": "tenant-a", "permissions": ["read"]},
    )
    api_key = key_resp.json()["raw_key"]

    search_resp = await test_client.get(
        "/v1/search",
        params={"record_type": "artist"},
        headers={"X-API-Key": api_key},
    )
    assert search_resp.status_code == 200
    items = search_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Alice Tenant A"


@pytest.mark.asyncio
async def test_usage_tracking_endpoint(test_client: AsyncClient):
    key_resp = await test_client.post(
        "/api/keys",
        json={"name": "usage-key", "tenant_id": "usage-tenant", "permissions": ["read"]},
    )
    api_key = key_resp.json()["raw_key"]

    for _ in range(2):
        await test_client.get("/v1/search", headers={"X-API-Key": api_key})

    usage_resp = await test_client.get("/api/usage", params={"tenant_id": "usage-tenant"})
    assert usage_resp.status_code == 200
    assert usage_resp.json()["total_requests"] >= 2
