import os

import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])
logger = structlog.get_logger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class SettingsResponse(BaseModel):
    artio_api_url: str | None
    artio_api_key_masked: str | None
    openai_api_key_masked: str | None
    max_crawl_depth: int
    max_pages_per_source: int
    crawl_delay_ms: int
    artio_configured: bool
    openai_configured: bool
    readonly: bool  # True on Vercel — settings managed via env vars


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mask_key(key: str | None) -> str | None:
    if not key:
        return None
    return f"***...{key[-4:]}" if len(key) > 4 else "****"


def _is_readonly() -> bool:
    """Vercel filesystem is read-only — detect via ENVIRONMENT=production."""
    return settings.environment == "production"


def _validate_env_target(env_file: str) -> None:
    env_dir = os.path.dirname(env_file) or "."
    if not os.path.isdir(env_dir):
        raise RuntimeError(f"Settings directory does not exist: {env_dir}")
    if os.path.exists(env_file):
        if not os.access(env_file, os.W_OK):
            raise RuntimeError(f"Settings file is not writable: {env_file}")
    elif not os.access(env_dir, os.W_OK):
        raise RuntimeError(f"Settings directory is not writable: {env_dir}")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    return SettingsResponse(
        artio_api_url=settings.artio_api_url,
        artio_api_key_masked=_mask_key(settings.artio_api_key),
        openai_api_key_masked=_mask_key(settings.openai_api_key),
        max_crawl_depth=settings.max_crawl_depth,
        max_pages_per_source=settings.max_pages_per_source,
        crawl_delay_ms=settings.crawl_delay_ms,
        artio_configured=bool(settings.artio_api_url and settings.artio_api_key),
        openai_configured=bool(settings.openai_api_key),
        readonly=_is_readonly(),
    )


@router.post("", response_model=SettingsResponse)
async def save_settings(body: SaveSettingsRequest) -> SettingsResponse:
    """
    Persist settings. On Vercel (readonly filesystem), only updates the
    in-memory settings object — changes won't survive a cold start.
    Configure permanent values via Vercel Environment Variables dashboard.
    """
    sent = body.model_fields_set
    readonly = _is_readonly()

    if not readonly:
        # Only write to .env file when running locally / on Docker
        from app.config import BASE_DIR
        from dotenv import set_key, unset_key

        env_file = str(BASE_DIR / ".env")
        try:
            _validate_env_target(env_file)

            if "artio_api_url" in sent:
                url = (body.artio_api_url or "").strip()
                if url:
                    set_key(env_file, "ARTIO_API_URL", url)
                else:
                    unset_key(env_file, "ARTIO_API_URL")

            if "artio_api_key" in sent and body.artio_api_key:
                key = body.artio_api_key.strip()
                if not key.startswith("***") and key:
                    set_key(env_file, "ARTIO_API_KEY", key)

            if "openai_api_key" in sent and body.openai_api_key:
                key = body.openai_api_key.strip()
                if not key.startswith("***") and key:
                    set_key(env_file, "OPENAI_API_KEY", key)

            if "max_crawl_depth" in sent and body.max_crawl_depth is not None:
                set_key(env_file, "MAX_CRAWL_DEPTH", str(body.max_crawl_depth))

            if "max_pages_per_source" in sent and body.max_pages_per_source is not None:
                set_key(env_file, "MAX_PAGES_PER_SOURCE", str(body.max_pages_per_source))

            if "crawl_delay_ms" in sent and body.crawl_delay_ms is not None:
                set_key(env_file, "CRAWL_DELAY_MS", str(body.crawl_delay_ms))
        except (OSError, PermissionError, ValueError, RuntimeError) as exc:
            logger.exception("settings_persist_failed", env_file=env_file, error=str(exc))
            raise HTTPException(
                status_code=500,
                detail="Failed to persist settings to .env. Check file path and permissions.",
            ) from exc

    # Always update in-memory settings
    if "artio_api_url" in sent:
        settings.artio_api_url = (body.artio_api_url or "").strip() or None

    if "artio_api_key" in sent and body.artio_api_key:
        key = body.artio_api_key.strip()
        if not key.startswith("***"):
            settings.artio_api_key = key or None

    if "openai_api_key" in sent and body.openai_api_key:
        key = body.openai_api_key.strip()
        if not key.startswith("***"):
            settings.openai_api_key = key

    if "max_crawl_depth" in sent and body.max_crawl_depth is not None:
        settings.max_crawl_depth = body.max_crawl_depth

    if "max_pages_per_source" in sent and body.max_pages_per_source is not None:
        settings.max_pages_per_source = body.max_pages_per_source

    if "crawl_delay_ms" in sent and body.crawl_delay_ms is not None:
        settings.crawl_delay_ms = body.crawl_delay_ms

    return await get_settings()


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
    except Exception as exc:
        return TestConnectionResponse(success=False, message=str(exc))
