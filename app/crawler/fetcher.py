import asyncio
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
import structlog

from app.config import is_serverless_environment, settings

logger = structlog.get_logger()

MAX_HTML_BYTES = 500 * 1024  # 500KB
USER_AGENT = "Artio-Miner/1.0"

# Per-domain last-request timestamps for rate limiting
_domain_last_request: dict[str, float] = {}
_domain_lock = asyncio.Lock()


@dataclass
class FetchResult:
    url: str
    final_url: str
    html: str
    status_code: int
    method: str  # "httpx" | "playwright"
    error: str | None = None
    etag: str | None = None
    last_modified: str | None = None


def _domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc


async def _respect_crawl_delay(domain: str) -> None:
    delay_s = settings.crawl_delay_ms / 1000
    async with _domain_lock:
        last = _domain_last_request.get(domain, 0)
        elapsed = time.time() - last
        if elapsed < delay_s:
            wait = delay_s - elapsed
        else:
            wait = 0
        _domain_last_request[domain] = time.time() + wait
    if wait > 0:
        await asyncio.sleep(wait)


def _truncate_html(html: str) -> tuple[str, bool]:
    encoded = html.encode("utf-8")
    if len(encoded) > MAX_HTML_BYTES:
        return encoded[:MAX_HTML_BYTES].decode("utf-8", errors="ignore"), True
    return html, False


async def _fetch_with_playwright(url: str) -> FetchResult:
    if is_serverless_environment():
        raise RuntimeError("This task must run in a worker environment, not Vercel.")

    from playwright.async_api import async_playwright

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({"User-Agent": USER_AGENT})
            response = await page.goto(url, wait_until="networkidle", timeout=30000)
            final_url = page.url
            html = await page.content()
            status_code = response.status if response else 0
            await browser.close()
        html, _ = _truncate_html(html)
        return FetchResult(
            url=url,
            final_url=final_url,
            html=html,
            status_code=status_code,
            method="playwright",
        )
    except Exception as exc:
        logger.error("playwright_fetch_error", url=url, error=str(exc))
        return FetchResult(
            url=url,
            final_url=url,
            html="",
            status_code=0,
            method="playwright",
            error=str(exc),
        )


async def fetch(url: str, use_playwright: bool = False) -> FetchResult:
    domain = _domain(url)
    await _respect_crawl_delay(domain)

    if use_playwright and settings.playwright_enabled:
        return await _fetch_with_playwright(url)

    try:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(url)
            final_url = str(resp.url)
            html = resp.text
            status_code = resp.status_code
            etag = resp.headers.get("etag")
            last_modified = resp.headers.get("last-modified")

        html_truncated, was_truncated = _truncate_html(html)

        # If body too small and playwright enabled, fall back
        if len(html.strip()) < 200 and settings.playwright_enabled:
            logger.info("playwright_fallback", url=url, reason="empty_body")
            return await _fetch_with_playwright(url)

        return FetchResult(
            url=url,
            final_url=final_url,
            html=html_truncated,
            status_code=status_code,
            method="httpx",
            etag=etag,
            last_modified=last_modified,
        )
    except Exception as exc:
        logger.error("httpx_fetch_error", url=url, error=str(exc))
        # Try playwright as fallback
        if settings.playwright_enabled:
            logger.info("playwright_fallback", url=url, reason="httpx_error")
            return await _fetch_with_playwright(url)
        return FetchResult(
            url=url,
            final_url=url,
            html="",
            status_code=0,
            method="httpx",
            error=str(exc),
        )
