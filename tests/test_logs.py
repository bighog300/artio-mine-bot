import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.log_writer import DatabaseLogProcessor
from app.db.models import Log


@pytest.mark.asyncio
async def test_create_log_entry(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://logs-create.com")
    @asynccontextmanager
    async def _session_factory():
        yield db_session

    processor = DatabaseLogProcessor(service_name="api", session_factory=_session_factory)
    await processor.start()
    processor(None, "info", {"event": "test log created", "source_id": source.id})
    await asyncio.sleep(0.05)
    await processor.stop()

    resp = await test_client.get("/api/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(item["message"] == "test log created" for item in data["items"])


@pytest.mark.asyncio
async def test_filter_by_level(test_client: AsyncClient, db_session: AsyncSession):
    db_session.add(Log(timestamp=datetime.now(UTC), level="info", service="api", message="info msg", context="{}"))
    db_session.add(Log(timestamp=datetime.now(UTC), level="error", service="api", message="error msg", context="{}"))
    await db_session.commit()

    resp = await test_client.get("/api/logs", params={"level": "error"})
    assert resp.status_code == 200
    assert all(item["level"] == "error" for item in resp.json()["items"])


@pytest.mark.asyncio
async def test_filter_by_source(test_client: AsyncClient, db_session: AsyncSession):
    source_a = await crud.create_source(db_session, url="https://logs-source-a.com")
    source_b = await crud.create_source(db_session, url="https://logs-source-b.com")

    db_session.add(Log(timestamp=datetime.now(UTC), level="info", service="api", source_id=source_a.id, message="a", context="{}"))
    db_session.add(Log(timestamp=datetime.now(UTC), level="info", service="api", source_id=source_b.id, message="b", context="{}"))
    await db_session.commit()

    resp = await test_client.get("/api/logs", params={"source_id": source_a.id})
    assert resp.status_code == 200
    assert all(item["source_id"] == source_a.id for item in resp.json()["items"])


@pytest.mark.asyncio
async def test_delete_old_logs(test_client: AsyncClient, db_session: AsyncSession):
    old_log = Log(
        timestamp=datetime.now(UTC) - timedelta(days=40),
        level="warning",
        service="worker",
        message="old log",
        context="{}",
    )
    fresh_log = Log(
        timestamp=datetime.now(UTC) - timedelta(days=2),
        level="warning",
        service="worker",
        message="new log",
        context="{}",
    )
    db_session.add(old_log)
    db_session.add(fresh_log)
    await db_session.commit()

    resp = await test_client.delete("/api/logs", params={"older_than_days": 30})
    assert resp.status_code == 200
    assert resp.json()["deleted_count"] >= 1

    list_resp = await test_client.get("/api/logs")
    messages = [item["message"] for item in list_resp.json()["items"]]
    assert "old log" not in messages


@pytest.mark.asyncio
async def test_log_pagination(test_client: AsyncClient, db_session: AsyncSession):
    for idx in range(10):
        db_session.add(
            Log(
                timestamp=datetime.now(UTC),
                level="debug",
                service="api",
                message=f"pagination-{idx}",
                context="{}",
            )
        )
    await db_session.commit()

    resp = await test_client.get("/api/logs", params={"skip": 3, "limit": 4})
    assert resp.status_code == 200
    data = resp.json()
    assert data["skip"] == 3
    assert data["limit"] == 4
    assert len(data["items"]) == 4
