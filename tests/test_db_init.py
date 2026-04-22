import pytest
from sqlalchemy import text

from app.config import settings
from app.db import database
from app.db.base import Base


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
