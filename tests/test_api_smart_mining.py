from unittest.mock import AsyncMock

import pytest

from app.ai.smart_miner import SmartMiner
from app.api.routes import smart_mining
from app.config import settings
from app.db import crud


@pytest.fixture(autouse=True)
def _smart_mine_env() -> None:
    smart_mining._miner = None
    previous_key = settings.openai_api_key
    settings.openai_api_key = "sk-proj-test-key"
    yield
    settings.openai_api_key = previous_key
    smart_mining._miner = None


@pytest.mark.asyncio
async def test_smart_mine_create_and_status(test_client):
    smart_mining._execute_smart_mine = AsyncMock(return_value=None)

    response = await test_client.post(
        "/api/smart-mine/",
        json={"url": "https://example.com", "name": "Example"},
    )
    assert response.status_code == 200
    source_id = response.json()["source_id"]

    status_resp = await test_client.get(f"/api/smart-mine/{source_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["source_id"] == source_id


@pytest.mark.asyncio
async def test_smart_mine_reuses_existing_source_by_url(test_client, db_session):
    smart_mining._execute_smart_mine = AsyncMock(return_value=None)
    source = await crud.create_source(db_session, url="https://example.com/reuse", name="Reuse")

    response = await test_client.post(
        "/api/smart-mine/",
        json={"url": source.url, "name": "Should Not Duplicate"},
    )

    assert response.status_code == 200
    assert response.json()["source_id"] == source.id


@pytest.mark.asyncio
async def test_template_endpoints(test_client):
    resp = await test_client.get("/api/smart-mine/templates")
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload["items"]) >= 1

    template_id = payload["items"][0]["id"]
    detail = await test_client.get(f"/api/smart-mine/templates/{template_id}")
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_retry_requires_retryable_status(test_client, db_session):
    source = await crud.create_source(db_session, url="https://retry.example", name="Retry")
    response = await test_client.post(f"/api/smart-mine/{source.id}/retry")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_smart_mine_metrics_endpoint(test_client):
    response = await test_client.get("/api/smart-mine/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert "cache" in payload
    assert "usage_totals" in payload
