import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import BASE_DIR, settings

router = APIRouter(prefix="/settings", tags=["settings"])

_ENV_FILE = BASE_DIR / ".env"


# ── Schemas ───────────────────────────────────────────────────────────────────


class SettingsResponse(BaseModel):
    artio_api_url: str | None
    artio_api_key_masked: str | None
    max_crawl_depth: int
    max_pages_per_source: int
    crawl_delay_ms: int
    artio_configured: bool


class SaveSettingsRequest(BaseModel):
    artio_api_url: str | None = None
    artio_api_key: str | None = None
    max_crawl_depth: int | None = None
    max_pages_per_source: int | None = None
    crawl_delay_ms: int | None = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mask_key(key: str | None) -> str | None:
    """Return a display-safe masked version of an API key."""
    if not key:
        return None
    return f"***...{key[-4:]}" if len(key) > 4 else "****"


def _set_env(key: str, value: str) -> None:
    from dotenv import set_key
    _ENV_FILE.touch(exist_ok=True)
    set_key(str(_ENV_FILE), key, value)


def _unset_env(key: str) -> None:
    from dotenv import unset_key
    if _ENV_FILE.exists():
        unset_key(str(_ENV_FILE), key)


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    return SettingsResponse(
        artio_api_url=settings.artio_api_url,
        artio_api_key_masked=_mask_key(settings.artio_api_key),
        max_crawl_depth=settings.max_crawl_depth,
        max_pages_per_source=settings.max_pages_per_source,
        crawl_delay_ms=settings.crawl_delay_ms,
        artio_configured=bool(settings.artio_api_url and settings.artio_api_key),
    )


@router.post("", response_model=SettingsResponse)
async def save_settings(body: SaveSettingsRequest) -> SettingsResponse:
    """
    Persist changed settings to .env and update the live settings object.

    Uses model_fields_set to distinguish "explicitly sent as null/empty" from
    "not included in the request body".
    API key: if submitted value starts with "***" it is the masked display value
    and is silently ignored (no update).
    """
    sent = body.model_fields_set

    if "artio_api_url" in sent:
        url = (body.artio_api_url or "").strip()
        if url:
            _set_env("ARTIO_API_URL", url)
            settings.artio_api_url = url
        else:
            _unset_env("ARTIO_API_URL")
            settings.artio_api_url = None

    if "artio_api_key" in sent and body.artio_api_key:
        key = body.artio_api_key.strip()
        if key.startswith("***"):
            pass  # masked display value — leave unchanged
        elif key:
            _set_env("ARTIO_API_KEY", key)
            settings.artio_api_key = key
        else:
            _unset_env("ARTIO_API_KEY")
            settings.artio_api_key = None

    if "max_crawl_depth" in sent and body.max_crawl_depth is not None:
        _set_env("MAX_CRAWL_DEPTH", str(body.max_crawl_depth))
        settings.max_crawl_depth = body.max_crawl_depth

    if "max_pages_per_source" in sent and body.max_pages_per_source is not None:
        _set_env("MAX_PAGES_PER_SOURCE", str(body.max_pages_per_source))
        settings.max_pages_per_source = body.max_pages_per_source

    if "crawl_delay_ms" in sent and body.crawl_delay_ms is not None:
        _set_env("CRAWL_DELAY_MS", str(body.crawl_delay_ms))
        settings.crawl_delay_ms = body.crawl_delay_ms

    return await get_settings()


@router.post("/test-artio", response_model=TestConnectionResponse)
async def test_artio_connection() -> TestConnectionResponse:
    """Probe the configured Artio API endpoint and report reachability."""
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
        return TestConnectionResponse(
            success=False, message="Connection refused — check the URL"
        )
    except httpx.TimeoutException:
        return TestConnectionResponse(success=False, message="Request timed out")
    except Exception as exc:
        return TestConnectionResponse(success=False, message=str(exc))
