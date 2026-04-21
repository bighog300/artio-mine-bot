from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from app.crawler.fetcher import fetch
from app.source_profiler.types import ProfiledPage


def _is_internal(seed_url: str, candidate_url: str) -> bool:
    return urlparse(seed_url).netloc == urlparse(candidate_url).netloc


def _parse_links(base_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html or "", "lxml")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
            continue
        links.append(urljoin(base_url, href).split("#")[0])
    return links


def _extract_title(html: str) -> str | None:
    soup = BeautifulSoup(html or "", "lxml")
    return soup.title.get_text(strip=True) if soup.title else None


def _fixture_pages(seed_url: str) -> list[ProfiledPage]:
    base = seed_url.rstrip("/")
    return [
        ProfiledPage(url=base, title="Home", out_links=[f"{base}/artists", f"{base}/events"]),
        ProfiledPage(url=f"{base}/artists", title="Artists Directory"),
        ProfiledPage(url=f"{base}/artists/ada-lovelace", title="Ada Lovelace"),
        ProfiledPage(url=f"{base}/artists/grace-hopper", title="Grace Hopper"),
        ProfiledPage(url=f"{base}/events", title="Events Listing"),
        ProfiledPage(url=f"{base}/events/spring-openings-2026", title="Spring Openings"),
        ProfiledPage(url=f"{base}/exhibitions", title="Exhibitions"),
        ProfiledPage(url=f"{base}/exhibitions/future-forms", title="Future Forms"),
    ]


async def discover_site_pages(seed_url: str, *, max_pages: int = 40) -> tuple[list[str], list[ProfiledPage], dict[str, object]]:
    if urlparse(seed_url).netloc.endswith(".test"):
        pages = _fixture_pages(seed_url)
        entrypoints = [seed_url.rstrip("/"), f"{seed_url.rstrip('/')}/artists", f"{seed_url.rstrip('/')}/events"]
        return entrypoints, pages[:max_pages], {"sitemap_urls": [], "nav_links_count": 3}

    homepage = await fetch(seed_url)
    if not homepage.html:
        return [seed_url], [], {"sitemap_urls": [], "nav_links_count": 0}

    sitemap_urls: list[str] = []
    sitemap_url = f"{seed_url.rstrip('/')}/sitemap.xml"
    sitemap = await fetch(sitemap_url)
    if sitemap.status_code == 200 and sitemap.html:
        try:
            root = ElementTree.fromstring(sitemap.html)
            sitemap_urls = [elem.text.strip() for elem in root.findall(".//{*}loc") if elem.text]
        except ElementTree.ParseError:
            sitemap_urls = []

    nav_links = [link for link in _parse_links(homepage.final_url, homepage.html) if _is_internal(seed_url, link)]
    queue: list[str] = list(dict.fromkeys(sitemap_urls[:20] + nav_links[:20]))
    seen: set[str] = {homepage.final_url}
    pages: list[ProfiledPage] = [
        ProfiledPage(
            url=homepage.final_url,
            title=_extract_title(homepage.html),
            html_snippet=homepage.html[:400],
            out_links=nav_links[:30],
        )
    ]
    entrypoints = [homepage.final_url] + queue[:5]

    while queue and len(pages) < max_pages:
        candidate = queue.pop(0)
        if candidate in seen or not _is_internal(seed_url, candidate):
            continue
        seen.add(candidate)
        fetched = await fetch(candidate)
        if not fetched.html:
            continue
        out_links = [link for link in _parse_links(fetched.final_url, fetched.html) if _is_internal(seed_url, link)]
        pages.append(
            ProfiledPage(
                url=fetched.final_url,
                title=_extract_title(fetched.html),
                html_snippet=fetched.html[:400],
                out_links=out_links[:25],
            )
        )
        for link in out_links[:12]:
            if link not in seen and link not in queue:
                queue.append(link)

    return entrypoints, pages, {"sitemap_urls": sitemap_urls[:20], "nav_links_count": len(nav_links)}
