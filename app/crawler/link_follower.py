import asyncio
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crawler.durable_frontier import run_durable_crawl
from app.crawler.robots import RobotsChecker
from app.crawler.site_mapper import SiteMap

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


def sanitize_html(html: str) -> str:
    if not html:
        return html
    sanitized_html = html.replace("\x00", "")
    return sanitized_html


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
    """Deprecated compatibility wrapper around the durable frontier crawler."""
    logger.warning(
        "link_follower_deprecated",
        source_id=source_id,
        message="crawl_source now delegates to run_durable_crawl",
    )
    if robots_checker is None:
        robots_checker = RobotsChecker()
    if max_pages is None:
        max_pages = settings.max_pages_per_source
    if max_depth is None:
        max_depth = settings.max_crawl_depth
    durable_stats = await run_durable_crawl(
        db,
        source_id=source_id,
        seed_url=site_map.root_url,
        job_id=None,
        worker_id="link-follower-compat",
        max_pages=max_pages,
        max_depth=max_depth,
        robots_checker=robots_checker,
    )
    return CrawlStats(
        pages_fetched=int(durable_stats.get("pages_crawled", 0)),
        pages_skipped=int(durable_stats.get("robots_blocked", 0)),
        pages_error=int(durable_stats.get("failed", 0)),
        urls_seen=set(),
    )
