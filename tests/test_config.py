import pytest

from app.config import (
    is_dev_auto_admin_enabled,
    is_development_environment,
    is_serverless_environment,
    normalize_database_url,
    validate_async_driver,
)


def test_normalize_postgres_sync_urls() -> None:
    assert normalize_database_url("postgresql://user:pw@host/db") == (
        "postgresql+asyncpg://user:pw@host/db"
    )
    assert normalize_database_url("postgresql+psycopg2://user:pw@host/db") == (
        "postgresql+asyncpg://user:pw@host/db"
    )


def test_validate_async_driver_rejects_sync_postgres() -> None:
    with pytest.raises(RuntimeError, match="postgresql\\+asyncpg://"):
        validate_async_driver("postgresql://user:pw@host/db")


def test_serverless_environment_helpers_treat_production_and_vercel_equally() -> None:
    assert is_serverless_environment("production") is True
    assert is_serverless_environment("vercel") is True
    assert is_serverless_environment("development") is False


def test_is_development_environment_helper() -> None:
    assert is_development_environment("development") is True
    assert is_development_environment("local") is True
    assert is_development_environment("dev") is True
    assert is_development_environment("production") is False


def test_dev_auto_admin_enabled_only_in_local_development() -> None:
    assert is_dev_auto_admin_enabled(environment="development", dev_auto_admin=None) is True
    assert is_dev_auto_admin_enabled(environment="development", dev_auto_admin=True) is True
    assert is_dev_auto_admin_enabled(environment="development", dev_auto_admin=False) is False
    assert is_dev_auto_admin_enabled(environment="production", dev_auto_admin=True) is False
    assert is_dev_auto_admin_enabled(environment="vercel", dev_auto_admin=True) is False
