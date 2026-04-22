import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.db.settings_store import get_setting, set_setting

router = APIRouter(prefix="/settings", tags=["settings"])
logger = structlog.get_logger(__name__)


class SettingsResponse(BaseModel):
    artio_api_url: str | None
    artio_api_key_masked: str | None
    openai_api_key_masked: str | None
    max_crawl_depth: int
    max_pages_per_source: int
    crawl_delay_ms: int
    artio_configured: bool
    openai_configured: bool


class SaveSettingsRequest(BaseModel):
    artio_api_url: str | None = None
    artio_api_key: str | None = None
    openai_api_key: str | None = None
    max_crawl_depth: int | None = None
    max_pages_per_source: int | None = None
    crawl_delay_ms: int | None = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


def _mask_key(key: str | None) -> str | None:
    if not key:
        return None
    return f"***...{key[-4:]}" if len(key) > 4 else "****"


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsResponse:
    artio_api_url = await get_setting(db, "artio_api_url")
    artio_api_key = await get_setting(db, "artio_api_key")
    openai_api_key = await get_setting(db, "openai_api_key")

    effective_artio_api_url = artio_api_url if artio_api_url is not None else settings.artio_api_url
    effective_artio_api_key = artio_api_key if artio_api_key is not None else settings.artio_api_key
    effective_openai_api_key = openai_api_key if openai_api_key is not None else settings.openai_api_key

    return SettingsResponse(
        artio_api_url=effective_artio_api_url,
        artio_api_key_masked=_mask_key(effective_artio_api_key),
        openai_api_key_masked=_mask_key(effective_openai_api_key),
        max_crawl_depth=settings.max_crawl_depth,
        max_pages_per_source=settings.max_pages_per_source,
        crawl_delay_ms=settings.crawl_delay_ms,
        artio_configured=bool(effective_artio_api_url and effective_artio_api_key),
        openai_configured=bool(effective_openai_api_key),
    )


@router.post("", response_model=SettingsResponse)
async def save_settings(
    body: SaveSettingsRequest,
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    sent = body.model_fields_set

    if "artio_api_url" in sent:
        settings.artio_api_url = (body.artio_api_url or "").strip() or None
        await set_setting(db, "artio_api_url", settings.artio_api_url)

    if "artio_api_key" in sent:
        settings.artio_api_key = (body.artio_api_key or "").strip() or None
        await set_setting(db, "artio_api_key", settings.artio_api_key)

    if "openai_api_key" in sent:
        settings.openai_api_key = (body.openai_api_key or "").strip() or None
        await set_setting(db, "openai_api_key", settings.openai_api_key)

    if "max_crawl_depth" in sent and body.max_crawl_depth is not None:
        if not 1 <= body.max_crawl_depth <= 10:
            raise HTTPException(status_code=400, detail="max_crawl_depth must be between 1 and 10")
        settings.max_crawl_depth = body.max_crawl_depth
        await set_setting(db, "max_crawl_depth", str(body.max_crawl_depth))

    if "max_pages_per_source" in sent and body.max_pages_per_source is not None:
        if not 1 <= body.max_pages_per_source <= 5000:
            raise HTTPException(status_code=400, detail="max_pages_per_source must be between 1 and 5000")
        settings.max_pages_per_source = body.max_pages_per_source
        await set_setting(db, "max_pages_per_source", str(body.max_pages_per_source))

    if "crawl_delay_ms" in sent and body.crawl_delay_ms is not None:
        if not 0 <= body.crawl_delay_ms <= 60000:
            raise HTTPException(status_code=400, detail="crawl_delay_ms must be between 0 and 60000")
        settings.crawl_delay_ms = body.crawl_delay_ms
        await set_setting(db, "crawl_delay_ms", str(body.crawl_delay_ms))

    await db.commit()
    return await get_settings(db)


@router.post("/test-artio", response_model=TestConnectionResponse)
async def test_artio_connection() -> TestConnectionResponse:
    if not settings.artio_api_url or not settings.artio_api_key:
        return TestConnectionResponse(
            success=False,
            message="Artio API URL and Key are not configured.",
        )

    url = settings.artio_api_url.rstrip("/") + "/health"
    headers = {"Authorization": f"Bearer {settings.artio_api_key}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code < 400:
            return TestConnectionResponse(
                success=True, message=f"Connected (HTTP {resp.status_code})"
            )
        return TestConnectionResponse(
            success=False, message=f"Server returned HTTP {resp.status_code}"
        )
    except httpx.ConnectError:
        return TestConnectionResponse(success=False, message="Connection refused — check the URL")
    except httpx.TimeoutException:
        return TestConnectionResponse(success=False, message="Request timed out")
    except httpx.HTTPError:
        logger.exception("settings_test_artio_request_failed")
        return TestConnectionResponse(success=False, message="Request failed")
