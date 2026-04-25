from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response

from app.crawler.fetcher import FetchResult, fetch
from app.crawler.automated_crawler import AutomatedCrawler
from app.crawler.crawl_policy import score_url
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


def test_crawl_policy_prioritizes_detail_over_utility():
    detail_score, detail_type = score_url("https://example.com/artists/john-doe")
    utility_score, utility_type = score_url("https://example.com/privacy")
    assert detail_type == "artist_profile"
    assert utility_type == "utility"
    assert detail_score > utility_score


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

    with patch("app.crawler.durable_frontier.fetch", new=AsyncMock(return_value=fetch_result)):
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

    with patch("app.crawler.durable_frontier.fetch", new=AsyncMock(return_value=fetch_result)):
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


@pytest.mark.asyncio
async def test_extract_deterministic_css_selectors():
    crawler = AutomatedCrawler(
        structure_map={
            "extraction_rules": {
                "artist_profile": {
                    "css_selectors": {
                        "name": "h1.artist-name",
                        "bio": "div.biography",
                    }
                }
            }
        },
        db=MagicMock(),
    )
    html = """
    <html><body>
      <h1 class="artist-name">Jane Doe</h1>
      <div class="biography">Painter and sculptor.</div>
    </body></html>
    """
    result = crawler._extract_deterministic(html, "artist_profile", "https://example.com/artists/jane-doe")
    assert result["data"]["name"] == "Jane Doe"
    assert result["data"]["bio"] == "Painter and sculptor."
    assert result["method"] == "deterministic"
    assert result["confidence"] == 100


@pytest.mark.asyncio
async def test_extract_deterministic_supports_attribute_fields():
    crawler = AutomatedCrawler(
        structure_map={
            "extraction_rules": {
                "artist_profile": {
                    "css_selectors": {
                        "title": "h1",
                        "description": "blockquote",
                        "email": "a[href^='mailto:']",
                        "website_url": "a.website",
                        "avatar_url": "img.avatar",
                        "source_url": "link[rel='canonical']",
                    }
                }
            }
        },
        db=MagicMock(),
    )
    html = """
    <html>
      <head><link rel="canonical" href="/michellesueur"></head>
      <body>
        <h1>Michelle Sueur</h1>
        <blockquote>South African mixed-media artist.</blockquote>
        <a href="mailto:artist@example.com?subject=hello">Email</a>
        <a class="website" href="https://portfolio.example.com">Website</a>
        <img class="avatar" src="/images/avatar.jpg" />
      </body>
    </html>
    """
    result = crawler._extract_deterministic(html, "artist_profile", "https://art.co.za/michellesueur")
    assert result["data"]["title"] == "Michelle Sueur"
    assert result["data"]["description"] == "South African mixed-media artist."
    assert result["data"]["email"] == "artist@example.com"
    assert result["data"]["website_url"] == "https://portfolio.example.com"
    assert result["data"]["avatar_url"] == "https://art.co.za/images/avatar.jpg"
    assert result["data"]["source_url"] == "https://art.co.za/michellesueur"
    assert result["confidence"] == 100


@pytest.mark.asyncio
async def test_extract_deterministic_regex():
    crawler = AutomatedCrawler(
        structure_map={
            "extraction_rules": {
                "artist_profile": {
                    "regex_patterns": {
                        "email": r"Email:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                    }
                }
            }
        },
        db=MagicMock(),
    )
    html = "<html><body><p>Email: artist@example.com</p></body></html>"
    result = crawler._extract_deterministic(html, "artist_profile", "https://example.com/artists/jane-doe")
    assert result["data"]["email"] == "artist@example.com"
    assert result["confidence"] == 100


@pytest.mark.asyncio
async def test_confidence_degradation():
    crawler = AutomatedCrawler(
        structure_map={
            "extraction_rules": {
                "artist_profile": {
                    "css_selectors": {"name": "h1.name", "bio": "div.bio", "contact": "div.contact"},
                    "regex_patterns": {"birth_year": r"Born (\\d{4})"},
                }
            }
        },
        db=MagicMock(),
    )
    result = crawler._extract_deterministic(
        "<html><body><h1>Wrong Selector</h1></body></html>",
        "artist_profile",
        "https://example.com/artists/a/jane-doe",
    )
    # 4 failures (3 css + 1 regex) => 100 - 40
    assert result["confidence"] == 60


@pytest.mark.asyncio
async def test_extract_with_ai_fallback():
    ai_client = AsyncMock()
    ai_client.complete = AsyncMock(return_value={"name": "Fallback Artist", "bio": "Fallback bio"})
    crawler = AutomatedCrawler(
        structure_map={
            "extraction_rules": {
                "artist_profile": {
                    "css_selectors": {
                        "name": "h1.missing",
                        "bio": "div.biography",
                        "mediums": "ul.mediums",
                        "contact": "div.contact",
                    }
                }
            }
        },
        db=MagicMock(),
        ai_client=ai_client,
    )
    extracted = crawler._extract_deterministic(
        "<html><body><h1>Missing class</h1></body></html>",
        "artist_profile",
        "https://example.com/artists/jane-doe",
    )
    assert extracted["confidence"] == 60
    assert extracted["confidence"] < 80
    assert extracted["method"] == "deterministic"
    fallback = await crawler._extract_with_ai("<html>content</html>", "artist_profile", "context")
    assert fallback["method"] == "ai_fallback"
    assert fallback["data"]["name"] == "Fallback Artist"


def test_classify_by_url():
    crawler = AutomatedCrawler(
        structure_map={
            "mining_map": {
                "artist_profile": {"url_pattern": "/artists/[name]"},
                "event_detail": {"url_pattern": "/events/[id]"},
            }
        },
        db=MagicMock(),
    )
    assert crawler._classify_by_url("https://example.com/artists/jane-doe") == "artist_profile"
    assert crawler._classify_by_url("https://example.com/events/123") == "event_detail"
    assert crawler._classify_by_url("https://example.com/about") == "unknown"


def test_classify_by_url_matches_numeric_tokens():
    crawler = AutomatedCrawler(
        structure_map={
            "mining_map": {
                "event_listing_page": {"url_pattern": "/events/page/[page]"},
                "archive_by_year_month": {"url_pattern": "/archive/[year]/[month]"},
            }
        },
        db=MagicMock(),
    )
    assert crawler._classify_by_url("https://example.com/events/page/12") == "event_listing_page"
    assert crawler._classify_by_url("https://example.com/archive/2026/04") == "archive_by_year_month"


def test_classify_by_url_prefers_more_specific_identifier_pattern():
    crawler = AutomatedCrawler(
        structure_map={
            "extraction_rules": {
                "artist_profile_hub": {"identifiers": ["/[name]/"], "css_selectors": {"name": "h1"}},
                "artist_biography": {"identifiers": ["/[name]/about.php"], "css_selectors": {"name": "h1"}},
            }
        },
        db=None,
        ai_client=AsyncMock(),
    )

    assert crawler._classify_by_url("https://www.art.co.za/cornevaneck/about.php") == "artist_biography"


@pytest.mark.asyncio
async def test_crawl_plan_execution(db_session):
    source = await crud.create_source(db_session, url="https://example.com")
    structure_map = {
        "crawl_targets": ["/artists/[letter]"],
        "mining_map": {
            "artist_profile": {"url_pattern": "/artists/[name]"},
            "artist_directory": {"url_pattern": "/artists/[letter]"},
        },
        "extraction_rules": {
            "artist_directory": {
                "css_selectors": {"title": "title"},
            }
        },
    }
    fetch_result = FetchResult(
        url="https://example.com/artists/a",
        final_url="https://example.com/artists/a",
        html="<html><head><title>Artists A</title></head><body><h1>A</h1></body></html>",
        status_code=200,
        method="httpx",
    )
    crawler = AutomatedCrawler(structure_map=structure_map, db=db_session, ai_client=AsyncMock())
    with patch("app.crawler.automated_crawler.fetch", new=AsyncMock(return_value=fetch_result)):
        with patch("app.crawler.automated_crawler.settings") as mock_settings:
            mock_settings.max_pages_per_source = 1
            mock_settings.deterministic_confidence_threshold = 80
            mock_settings.crawler_use_ai_fallback = False
            mock_settings.max_ai_fallback_per_source = 50
            stats = await crawler.execute_crawl_plan(source.id)

    assert stats["pages_crawled"] == 1
    assert stats["extracted_deterministic"] == 1
    pages = await crud.list_pages(db_session, source_id=source.id, limit=10)
    assert len(pages) == 1


@pytest.mark.asyncio
async def test_save_record_persists_artist_metadata_fields(db_session):
    source = await crud.create_source(db_session, url="https://art.co.za", name="Art")
    crawler = AutomatedCrawler(structure_map={"extraction_rules": {}}, db=db_session)

    record = await crawler._save_record(
        source_id=source.id,
        page_id=None,
        page_type="artist_profile",
        data={
            "method": "deterministic",
            "confidence": 92,
            "data": {
                "title": "Michelle Sueur",
                "description": "Painter and sculptor",
                "bio": "Long-form bio",
                "email": "artist@example.com",
                "website_url": "https://portfolio.example.com",
                "avatar_url": "https://art.co.za/images/avatar.jpg",
                "source_url": "https://art.co.za/michellesueur",
            },
        },
        url="https://art.co.za/michellesueur",
    )

    assert record.title == "Michelle Sueur"
    assert record.description == "Long-form bio"
    assert record.bio == "Long-form bio"
    assert record.email == "artist@example.com"
    assert record.website_url == "https://portfolio.example.com"
    assert record.avatar_url == "https://art.co.za/images/avatar.jpg"
    assert record.source_url == "https://art.co.za/michellesueur"
