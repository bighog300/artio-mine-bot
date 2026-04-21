import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.main import app
from app.api.deps import get_db


@pytest.mark.asyncio
async def test_spoofed_role_header_does_not_grant_access(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/sources", headers={"X-Role": "admin"})
    app.dependency_overrides.clear()
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_keys_route_requires_auth(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/keys")
    app.dependency_overrides.clear()
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_keys_route_forbids_non_admin_api_key(test_client: AsyncClient, db_session: AsyncSession):
    create_resp = await test_client.post(
        "/api/keys",
        json={"name": "viewer-key", "tenant_id": "viewer-tenant", "permissions": ["read"]},
    )
    raw_key = create_resp.json()["raw_key"]

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": raw_key},
    ) as client:
        resp = await client.get("/api/keys")
    app.dependency_overrides.clear()
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_api_keys_route_allows_admin_token(test_client: AsyncClient):
    resp = await test_client.get("/api/keys")
    assert resp.status_code == 200
