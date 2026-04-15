from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response

from app.crawler.fetcher import FetchResult, fetch
from app.crawler.link_follower import CrawlQueue, _extract_links
from app.crawler.robots import RobotsChecker
from app.crawler.site_mapper import _extract_nav_links
from app.db import crud

SAMPLE_HTML = """
<html>
<head><title>Test Page</title></head>
<body>
<nav>
  <a href="/artists">Artists</a>
  <a href="/events">Events</a>
  <a href="https://external.com/page">External</a>
</nav>
<main>
  <p>Content here</p>
  <a href="/artists/john-doe">John Doe</a>
  <a href="/events/opening-night">Opening Night</a>
</main>
</body>
</html>
"""

MINIMAL_HTML = "<html><body>x</body></html>"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_httpx_success():
    respx.get("https://example.com/page").mock(
        return_value=Response(200, text=SAMPLE_HTML)
    )
    with patch("app.crawler.fetcher.settings") as mock_settings:
        mock_settings.crawl_delay_ms = 0
        mock_settings.playwright_enabled = False
        result = await fetch("https://example.com/page")
    assert result.status_code == 200
    assert result.method == "httpx"
    assert result.error is None
    assert "Test Page" in result.html


@pytest.mark.asyncio
@respx.mock
async def test_fetch_playwright_fallback():
    # Return tiny response to trigger playwright fallback
    respx.get("https://example.com/js-page").mock(
        return_value=Response(200, text="<html></html>")
    )
    playwright_result = FetchResult(
        url="https://example.com/js-page",
        final_url="https://example.com/js-page",
        html=SAMPLE_HTML,
        status_code=200,
        method="playwright",
    )
    with patch("app.crawler.fetcher.settings") as mock_settings:
        mock_settings.crawl_delay_ms = 0
        mock_settings.playwright_enabled = True
        with patch("app.crawler.fetcher._fetch_with_playwright", new=AsyncMock(return_value=playwright_result)):
            result = await fetch("https://example.com/js-page")
    assert result.method == "playwright"
    assert result.html == SAMPLE_HTML


@pytest.mark.asyncio
async def test_robots_blocked():
    robots_txt = "User-agent: *\nDisallow: /private/"
    checker = RobotsChecker()
    with respx.mock:
        respx.get("https://example.com/robots.txt").mock(
            return_value=Response(200, text=robots_txt)
        )
        allowed = await checker.is_allowed("https://example.com/private/secret")
    assert allowed is False


@pytest.mark.asyncio
async def test_robots_allowed():
    robots_txt = "User-agent: *\nDisallow: /admin/"
    checker = RobotsChecker()
    with respx.mock:
        respx.get("https://testsite.com/robots.txt").mock(
            return_value=Response(200, text=robots_txt)
        )
        allowed = await checker.is_allowed("https://testsite.com/artists/")
    assert allowed is True


def test_link_extraction():
    base = "https://example.com"
    links = _extract_links(SAMPLE_HTML, base)
    # Should include same-domain links only
    assert "https://example.com/artists" in links
    assert "https://example.com/events" in links
    assert "https://example.com/artists/john-doe" in links
    # External link should be excluded
    assert "https://external.com/page" not in links


@pytest.mark.asyncio
async def test_crawl_respects_max_pages(db_session):
    from app.crawler.link_follower import crawl_source
    from app.crawler.site_mapper import Section, SiteMap

    site_map = SiteMap(
        root_url="https://example.com",
        sections=[
            Section(
                name="Artists",
                url="https://example.com/artists",
                content_type="artist_directory",
                confidence=80,
            )
        ],
    )

    fetch_result = FetchResult(
        url="https://example.com/artists",
        final_url="https://example.com/artists",
        html=SAMPLE_HTML,
        status_code=200,
        method="httpx",
    )

    robots_checker = RobotsChecker()
    source = await __import__("app.db.crud", fromlist=["create_source"]).create_source(
        db_session, url="https://example.com"
    )

    with patch("app.crawler.link_follower.fetch", new=AsyncMock(return_value=fetch_result)):
        with patch.object(robots_checker, "is_allowed", new=AsyncMock(return_value=True)):
            stats = await crawl_source(
                source_id=source.id,
                site_map=site_map,
                db=db_session,
                robots_checker=robots_checker,
                max_pages=2,
                max_depth=1,
            )

    assert stats.pages_fetched <= 2


@pytest.mark.asyncio
async def test_crawl_sanitizes_null_bytes_before_store(db_session):
    from app.crawler.link_follower import crawl_source
    from app.crawler.site_mapper import Section, SiteMap

    site_map = SiteMap(
        root_url="https://example.com",
        sections=[
            Section(
                name="Artists",
                url="https://example.com/artists",
                content_type="artist_directory",
                confidence=80,
            )
        ],
    )
    source = await crud.create_source(db_session, url="https://example.com")
    fetch_result = FetchResult(
        url="https://example.com/artists",
        final_url="https://example.com/artists",
        html="<html><body>Hello\x00World</body></html>",
        status_code=200,
        method="httpx",
    )
    robots_checker = RobotsChecker()

    with patch("app.crawler.link_follower.fetch", new=AsyncMock(return_value=fetch_result)):
        with patch.object(robots_checker, "is_allowed", new=AsyncMock(return_value=True)):
            stats = await crawl_source(
                source_id=source.id,
                site_map=site_map,
                db=db_session,
                robots_checker=robots_checker,
                max_pages=1,
                max_depth=0,
            )

    assert stats.pages_error == 0
    pages = await crud.list_pages(db_session, source_id=source.id, limit=10)
    stored_page = next(page for page in pages if page.url == "https://example.com/artists")
    assert stored_page is not None
    assert stored_page.status == "fetched"
    assert stored_page.html is not None
    assert "\x00" not in stored_page.html
    assert stored_page.html == "<html><body>HelloWorld</body></html>"


def test_generate_urls_from_pattern_letter_and_page():
    from app.crawler.site_structure_analyzer import _generate_urls_from_pattern

    letter_urls = _generate_urls_from_pattern("https://example.com", "/artists/[letter]")
    assert letter_urls[0] == "https://example.com/artists/a"
    assert letter_urls[-1] == "https://example.com/artists/z"
    assert len(letter_urls) == 26

    page_urls = _generate_urls_from_pattern("https://example.com", "/artists?page=[page]", limit=3)
    assert page_urls == [
        "https://example.com/artists?page=1",
        "https://example.com/artists?page=2",
        "https://example.com/artists?page=3",
    ]


def test_extract_nav_html_only_returns_nav_and_header_content():
    from app.crawler.site_structure_analyzer import _extract_nav_html

    html = """
    <html><body>
      <header><a href='/artists'>Artists</a></header>
      <main><a href='/hidden'>Hidden</a></main>
      <nav><a href='/events'>Events</a></nav>
    </body></html>
    """
    result = _extract_nav_html(html)
    assert "Artists" in result
    assert "Events" in result
    assert "Hidden" not in result
