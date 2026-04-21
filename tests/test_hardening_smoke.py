from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.main import app
from app.config import settings
from app.db import crud


@pytest.mark.asyncio
async def test_smoke_admin_route_requires_verified_auth(db_session: AsyncSession):
    original_dev_auto_admin = settings.dev_auto_admin
    try:
        settings.dev_auto_admin = False

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            unauth = await client.get("/api/sources")
    finally:
        app.dependency_overrides.clear()
        settings.dev_auto_admin = original_dev_auto_admin

    assert unauth.status_code == 401


@pytest.mark.asyncio
async def test_smoke_api_key_crud_protected_for_non_admin(
    test_client: AsyncClient,
    db_session: AsyncSession,
):
    create_resp = await test_client.post(
        "/api/keys",
        json={"name": "smoke-viewer", "tenant_id": "smoke-tenant", "permissions": ["read"]},
    )
    assert create_resp.status_code == 201
    viewer_key = create_resp.json()["raw_key"]

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": viewer_key},
    ) as client:
        list_resp = await client.get("/api/keys")
    app.dependency_overrides.clear()

    assert list_resp.status_code == 403


@pytest.mark.asyncio
async def test_smoke_page_dispatch_and_health_and_settings(
    test_client: AsyncClient,
    db_session: AsyncSession,
):
    source = await crud.create_source(db_session, url="https://smoke-pages.com")
    page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://smoke-pages.com/1",
        original_url="https://smoke-pages.com/1",
        html="<html><body>smoke</body></html>",
        status="fetched",
    )

    with patch("app.api.routes.pages._enqueue_page_job", return_value="rq-smoke-1"):
        reclassify = await test_client.post(f"/api/pages/{page.id}/reclassify")
    assert reclassify.status_code == 202
    assert reclassify.json()["status"] == "queued"

    health_resp = await test_client.get("/health")
    assert health_resp.status_code == 200
    health_payload = health_resp.json()
    assert {"status", "db", "redis", "workers"}.issubset(health_payload.keys())

    settings_resp = await test_client.post(
        "/api/settings",
        json={"openai_api_key": "sk-should-not-save"},
    )
    assert settings_resp.status_code == 400
