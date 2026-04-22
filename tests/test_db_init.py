import pytest
from sqlalchemy import text

from app.config import settings
from app.api.main import lifespan
from app.db import database
from app.db.base import Base
from fastapi import FastAPI


@pytest.mark.asyncio
async def test_init_db_does_not_create_schema(monkeypatch: pytest.MonkeyPatch):
    """App startup must not call metadata.create_all()."""

    called = False

    def _create_all_guard(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("init_db should not call Base.metadata.create_all")

    monkeypatch.setattr(Base.metadata, "create_all", _create_all_guard)

    await database.init_db()

    assert called is False


@pytest.mark.asyncio
async def test_init_db_seeds_public_tenant_and_loads_user_settings():
    """Bootstrap data logic should still run after schema already exists."""

    async with database.get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.exec_driver_sql("DELETE FROM tenants")
        await conn.exec_driver_sql(
            "INSERT INTO settings (key, value, updated_at) VALUES ('artio_api_url', 'https://seeded.example', CURRENT_TIMESTAMP)"
        )

    previous_artio_url = settings.artio_api_url

    try:
        await database.init_db()

        async with database.AsyncSessionLocal() as session:
            tenant_count = await session.scalar(text("SELECT COUNT(*) FROM tenants WHERE id='public'"))

        assert tenant_count == 1
        assert settings.artio_api_url == "https://seeded.example"
    finally:
        settings.artio_api_url = previous_artio_url


@pytest.mark.asyncio
async def test_startup_does_not_run_init_db_in_production(monkeypatch: pytest.MonkeyPatch):
    called_init = False

    async def _fake_init_db() -> None:
        nonlocal called_init
        called_init = True

    async def _fake_wait_for_database() -> None:
        return None

    monkeypatch.setattr("app.db.database.init_db", _fake_init_db)
    monkeypatch.setattr("app.db.database.wait_for_database", _fake_wait_for_database)

    previous_environment = settings.environment
    previous_run_startup_db_init = settings.run_startup_db_init
    previous_db_startup_wait_enabled = settings.db_startup_wait_enabled
    settings.environment = "production"
    settings.run_startup_db_init = True
    settings.db_startup_wait_enabled = True

    try:
        async with lifespan(FastAPI()):
            pass
        assert called_init is False
    finally:
        settings.environment = previous_environment
        settings.run_startup_db_init = previous_run_startup_db_init
        settings.db_startup_wait_enabled = previous_db_startup_wait_enabled
