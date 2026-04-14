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
TERMINAL_PAGE_STATUSES = {"extracted", "skipped"}


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

    def size(self) -> int:
        return self._queue.qsize()

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
    source = await crud.wait_for_source(db, source_id, retries=3, delay_seconds=0.2)
    if source is None:
        raise ValueError(f"Source {source_id} not found before crawl page storage")
    root_url = source.url or site_map.root_url

    # Seed queue with section URLs
    for section in site_map.sections:
        queue.add(section.url, depth=0)

    # Always seed from root URL to guarantee at least one crawl target.
    if root_url:
        queue.add(root_url, depth=0)
        root_page, root_created = await crud.get_or_create_page(db, source_id=source_id, url=root_url)
        if root_created:
            await crud.update_page(
                db,
                root_page.id,
                original_url=root_url,
                status="fetched",
                depth=0,
            )
            logger.info("page_created", source_id=source_id, page_id=root_page.id, url=root_url)

    logger.info("crawl_started", source_id=source_id, frontier_size=queue.size())

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
                await db.rollback()
            continue

        # Store page
        try:
            page, created = await crud.get_or_create_page(
                db, source_id=source_id, url=result.final_url
            )
            if created:
                logger.info("page_created", source_id=source_id, page_id=page.id, url=result.final_url)
            title = _extract_title(result.html)
            update_kwargs = {
                "original_url": url,
                "fetch_method": result.method,
                "html": result.html,
                "html_truncated": len(result.html.encode()) >= 500 * 1024,
                "title": title,
                "depth": depth,
            }
            if page.status not in TERMINAL_PAGE_STATUSES:
                update_kwargs["status"] = "fetched"
            else:
                logger.info(
                    "crawl_page_preserve_terminal_status",
                    source_id=source_id,
                    page_id=page.id,
                    url=result.final_url,
                    status=page.status,
                )
            await crud.update_page(db, page.id, **update_kwargs)
            logger.info("page_fetched", source_id=source_id, page_id=page.id, url=result.final_url)
        except Exception as exc:
            logger.error("store_page_error", url=url, error=str(exc))
            await db.rollback()
            source_exists = await crud.get_source(db, source_id)
            if source_exists is None:
                logger.error("store_page_source_missing", source_id=source_id, url=url)
                raise ValueError(
                    f"Source {source_id} no longer exists while storing crawled pages"
                ) from exc
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
        total_pages = await crud.count_pages(db, source_id=source_id)
        await crud.update_source(db, source_id, total_pages=total_pages)
    except Exception:
        await db.rollback()

    logger.info(
        "crawl_complete",
        source_id=source_id,
        fetched=stats.pages_fetched,
        skipped=stats.pages_skipped,
        errors=stats.pages_error,
    )
    return stats
