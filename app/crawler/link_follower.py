import asyncio
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crawler.fetcher import FetchResult, fetch
from app.crawler.robots import RobotsChecker
from app.crawler.site_mapper import SiteMap
from app.db import crud

logger = structlog.get_logger()


@dataclass
class CrawlStats:
    pages_fetched: int = 0
    pages_skipped: int = 0
    pages_error: int = 0
    urls_seen: set[str] = field(default_factory=set)


def _same_domain(base: str, url: str) -> bool:
    return urlparse(base).netloc == urlparse(url).netloc


def _extract_links(html: str, base_url: str) -> list[str]:
    """Extract all same-domain links from a page."""
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        full_url = urljoin(base_url, href)
        # Strip fragments
        full_url = full_url.split("#")[0]
        if not full_url.startswith("http"):
            continue
        if _same_domain(base_url, full_url):
            links.append(full_url)
    return links


def _extract_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)
    return None


class CrawlQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        self._seen: set[str] = set()

    def add(self, url: str, depth: int = 0) -> bool:
        """Add URL to queue if not seen. Returns True if added."""
        if url in self._seen:
            return False
        self._seen.add(url)
        self._queue.put_nowait((url, depth))
        return True

    async def get(self) -> tuple[str, int] | None:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def empty(self) -> bool:
        return self._queue.empty()

    @property
    def seen(self) -> set[str]:
        return self._seen


async def crawl_source(
    source_id: str,
    site_map: SiteMap,
    db: AsyncSession,
    robots_checker: RobotsChecker | None = None,
    max_pages: int | None = None,
    max_depth: int | None = None,
) -> CrawlStats:
    """Crawl all sections in a SiteMap, storing pages in DB."""
    if robots_checker is None:
        robots_checker = RobotsChecker()
    if max_pages is None:
        max_pages = settings.max_pages_per_source
    if max_depth is None:
        max_depth = settings.max_crawl_depth

    stats = CrawlStats()
    queue = CrawlQueue()

    # Seed queue with section URLs
    for section in site_map.sections:
        queue.add(section.url, depth=0)

    # Also seed from root
    queue.add(site_map.root_url, depth=0)

    while not queue.empty() and stats.pages_fetched < max_pages:
        item = await queue.get()
        if item is None:
            break
        url, depth = item

        # Check robots.txt
        allowed = await robots_checker.is_allowed(url)
        if not allowed:
            logger.info("robots_blocked", url=url)
            stats.pages_skipped += 1
            continue

        # Fetch page
        result: FetchResult = await fetch(url)

        if result.error:
            logger.warning("fetch_error", url=url, error=result.error)
            stats.pages_error += 1
            # Create page record with error status
            try:
                await crud.create_page(
                    db,
                    source_id=source_id,
                    url=result.final_url or url,
                    original_url=url,
                    status="error",
                    error_message=result.error,
                    depth=depth,
                )
            except Exception:
                pass
            continue

        # Store page
        try:
            page, created = await crud.get_or_create_page(
                db, source_id=source_id, url=result.final_url
            )
            title = _extract_title(result.html)
            await crud.update_page(
                db,
                page.id,
                original_url=url,
                status="fetched",
                fetch_method=result.method,
                html=result.html,
                html_truncated=len(result.html.encode()) >= 500 * 1024,
                title=title,
                depth=depth,
            )
        except Exception as exc:
            logger.error("store_page_error", url=url, error=str(exc))
            stats.pages_error += 1
            continue

        stats.pages_fetched += 1

        # Extract links for next depth
        if depth < max_depth:
            links = _extract_links(result.html, result.final_url)
            for link in links:
                queue.add(link, depth=depth + 1)

    # Update source stats
    try:
        await crud.update_source(db, source_id, total_pages=stats.pages_fetched)
    except Exception:
        pass

    logger.info(
        "crawl_complete",
        source_id=source_id,
        fetched=stats.pages_fetched,
        skipped=stats.pages_skipped,
        errors=stats.pages_error,
    )
    return stats
