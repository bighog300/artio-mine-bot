from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()


@dataclass
class Section:
    name: str
    url: str
    content_type: str
    pagination_type: str = "none"
    index_pattern: str | None = None
    confidence: int = 0


@dataclass
class SiteMap:
    root_url: str
    platform: str = "unknown"
    sections: list[Section] = field(default_factory=list)


def _same_domain(base: str, url: str) -> bool:
    return urlparse(base).netloc == urlparse(url).netloc


def _extract_nav_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Extract (text, url) pairs from nav/header/footer elements."""
    soup = BeautifulSoup(html, "lxml")
    links: list[tuple[str, str]] = []
    seen: set[str] = set()

    for container in soup.find_all(["nav", "header", "footer"]):
        for a in container.find_all("a", href=True):
            href = a.get("href", "").strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            full_url = urljoin(base_url, href)
            # Only same-domain internal links
            if not _same_domain(base_url, full_url):
                continue
            if full_url in seen:
                continue
            seen.add(full_url)
            text = a.get_text(strip=True)
            links.append((text, full_url))

    return links


def _extract_home_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Extract (text, url) pairs from all links on homepage as fallback."""
    soup = BeautifulSoup(html, "lxml")
    links: list[tuple[str, str]] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        full_url = urljoin(base_url, href).split("#")[0]
        if not _same_domain(base_url, full_url):
            continue
        if full_url in seen:
            continue
        seen.add(full_url)
        text = a.get_text(strip=True) or full_url.rsplit("/", 1)[-1]
        links.append((text, full_url))

    return links


CONTENT_TYPE_PATTERNS = [
    ("artist_directory", ["/artists", "/artist", "/our-artists", "/gallery-artists"]),
    ("event_listing", ["/events", "/event", "/whats-on", "/what-s-on", "/what's-on", "/upcoming"]),
    (
        "exhibition_listing",
        ["/exhibitions", "/exhibition", "/shows", "/current-shows", "/past-shows"],
    ),
    ("artwork_listing", ["/artworks", "/artwork", "/shop", "/works", "/portfolio", "/gallery"]),
    ("venue_profile", ["/venue", "/about", "/contact", "/gallery-info"]),
]

PAGINATION_PATTERNS = [
    ("letter", ["?letter=", "/a-z", "?page=a", "[a-z]"]),
    ("numbered", ["?page=", "/page/", "?p="]),
]


def _classify_section(name: str, url: str) -> tuple[str, str, str | None, int]:
    """Returns (content_type, pagination_type, index_pattern, confidence)."""
    url_lower = url.lower()
    name_lower = name.lower()

    for content_type, patterns in CONTENT_TYPE_PATTERNS:
        for pattern in patterns:
            if pattern in url_lower or pattern.strip("/") in name_lower:
                # Detect pagination
                for pag_type, pag_patterns in PAGINATION_PATTERNS:
                    for pp in pag_patterns:
                        if pp in url_lower:
                            return content_type, pag_type, None, 75
                return content_type, "none", None, 70

    return "unknown", "none", None, 30


async def map_site(url: str, ai_client=None, html: str | None = None) -> SiteMap:
    """Map a site's structure from its homepage."""
    from app.crawler.fetcher import fetch

    if html is None:
        result = await fetch(url)
        html = result.html
        if not html:
            logger.warning("map_site_empty_html", url=url)
            return SiteMap(root_url=url)

    nav_links = _extract_nav_links(html, url)
    logger.info("map_site_nav_links", url=url, count=len(nav_links))
    if not nav_links:
        nav_links = _extract_home_links(html, url)
        logger.info("map_site_nav_links_fallback_home_links", url=url, count=len(nav_links))

    sections: list[Section] = []
    seen_types: set[str] = set()

    # Try AI classification first
    if ai_client is not None:
        try:
            nav_html = _get_nav_html(html)
            from app.ai.client import SITE_MAPPER_PROMPT

            response = await ai_client.complete(
                system_prompt=SITE_MAPPER_PROMPT,
                user_content=f"Homepage URL: {url}\n\nNav HTML:\n{nav_html[:3000]}",
                response_format={"type": "json_object"},
            )
            platform = response.get("platform", "unknown")
            for s in response.get("sections", []):
                sections.append(
                    Section(
                        name=s.get("name", "Unknown"),
                        url=s.get("url", url),
                        content_type=s.get("content_type", "unknown"),
                        pagination_type=s.get("pagination_type", "none"),
                        index_pattern=s.get("index_pattern"),
                        confidence=s.get("confidence", 0),
                    )
                )
            return SiteMap(root_url=url, platform=platform, sections=sections)
        except Exception as exc:
            logger.warning("site_mapper_ai_failed", error=str(exc))

    # Heuristic fallback
    platform = "unknown"
    soup = BeautifulSoup(html, "lxml")
    if soup.find(attrs={"class": lambda c: c and "wp-" in c}):
        platform = "wordpress"

    for name, link_url in nav_links:
        if not name or len(name) < 2:
            continue
        content_type, pag_type, index_pattern, confidence = _classify_section(name, link_url)
        if content_type == "unknown":
            continue
        if content_type in seen_types:
            continue
        seen_types.add(content_type)
        sections.append(
            Section(
                name=name,
                url=link_url,
                content_type=content_type,
                pagination_type=pag_type,
                index_pattern=index_pattern,
                confidence=confidence,
            )
        )

    logger.info("map_site_sections", url=url, count=len(sections))
    return SiteMap(root_url=url, platform=platform, sections=sections)


def _get_nav_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    parts = []
    for tag in soup.find_all(["nav", "header"]):
        parts.append(str(tag))
    return "\n".join(parts)
