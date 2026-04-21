import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.api.main import app
from app.api.deps import get_db


@pytest.mark.asyncio
async def test_spoofed_role_header_does_not_grant_access(db_session: AsyncSession):
    original_dev_auto_admin = settings.dev_auto_admin
    settings.dev_auto_admin = False

    async def override_get_db():
        yield db_session

    try:
        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/sources", headers={"X-Role": "admin"})
    finally:
        app.dependency_overrides.clear()
        settings.dev_auto_admin = original_dev_auto_admin
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_keys_route_requires_auth(db_session: AsyncSession):
    original_dev_auto_admin = settings.dev_auto_admin
    settings.dev_auto_admin = False

    async def override_get_db():
        yield db_session

    try:
        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/keys")
    finally:
        app.dependency_overrides.clear()
        settings.dev_auto_admin = original_dev_auto_admin
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
async def test_api_key_auth_still_allows_protected_read_routes(
    test_client: AsyncClient, db_session: AsyncSession
):
    create_resp = await test_client.post(
        "/api/keys",
        json={"name": "reader-key", "tenant_id": "reader-tenant", "permissions": ["read"]},
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
        resp = await client.get("/api/sources")
    app.dependency_overrides.clear()
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_keys_route_allows_admin_token(test_client: AsyncClient):
    resp = await test_client.get("/api/keys")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dev_auto_admin_allows_access_without_auth_in_development(db_session: AsyncSession):
    original_environment = settings.environment
    original_dev_auto_admin = settings.dev_auto_admin
    try:
        settings.environment = "development"
        settings.dev_auto_admin = True

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/sources")
    finally:
        app.dependency_overrides.clear()
        settings.environment = original_environment
        settings.dev_auto_admin = original_dev_auto_admin
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dev_auto_admin_disabled_in_development_requires_auth(db_session: AsyncSession):
    original_environment = settings.environment
    original_dev_auto_admin = settings.dev_auto_admin
    try:
        settings.environment = "development"
        settings.dev_auto_admin = False

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/sources")
    finally:
        app.dependency_overrides.clear()
        settings.environment = original_environment
        settings.dev_auto_admin = original_dev_auto_admin
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dev_auto_admin_never_enabled_in_strict_env_even_if_flag_true(db_session: AsyncSession):
    original_environment = settings.environment
    original_dev_auto_admin = settings.dev_auto_admin
    for environment_name in ("production", "vercel"):
        try:
            settings.environment = environment_name
            settings.dev_auto_admin = True

            async def override_get_db():
                yield db_session

            app.dependency_overrides[get_db] = override_get_db
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/sources")
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.clear()
            settings.environment = original_environment
            settings.dev_auto_admin = original_dev_auto_admin
