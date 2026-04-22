from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Settings

USER_CONFIGURABLE_KEYS = [
    "artio_api_url",
    "artio_api_key",
    "openai_api_key",
]


async def get_setting(session: AsyncSession, key: str) -> str | None:
    setting = await session.get(Settings, key)
    if setting is None:
        return None
    return setting.value


async def set_setting(session: AsyncSession, key: str, value: str | None) -> None:
    setting = await session.get(Settings, key)
    if setting is None:
        session.add(Settings(key=key, value=value))
    else:
        setting.value = value
        setting.updated_at = func.now()


async def load_user_settings(session: AsyncSession) -> dict[str, str | None]:
    result = await session.execute(select(Settings).where(Settings.key.in_(USER_CONFIGURABLE_KEYS)))
    rows = {row.key: row.value for row in result.scalars()}
    return {key: rows.get(key) for key in USER_CONFIGURABLE_KEYS}
