import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import Page


@pytest.fixture
def mock_ai_client():
    client = MagicMock()
    client.complete = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_full_pipeline_happy_path(db_session: AsyncSession, mock_ai_client):
    from app.ai.classifier import ClassifyResult
    from app.crawler.fetcher import FetchResult
    from app.crawler.site_mapper import Section, SiteMap
    from app.pipeline.runner import PipelineRunner

    source = await crud.create_source(db_session, url="https://example.com", name="Test")
    await crud.update_source(
        db_session,
        source.id,
        structure_map=json.dumps(
            {
                "crawl_plan": {
                    "phases": [
                        {
                            "phase_name": "Artists Directory",
                            "base_url": "https://example.com",
                            "url_pattern": "/artists/john",
                            "pagination_type": "none",
                            "num_pages": 1,
                        }
                    ]
                },
                "extraction_rules": {
                    "artist_profile": {
                        "css_selectors": {
                            "name": "p",
                            "bio": "p",
                        },
                        "identifiers": ["URL matches /artists/"],
                    }
                },
                "directory_structure": "test structure",
            }
        ),
    )

    sample_html = """<html><head><title>Artist</title></head><body>
    <img src="https://example.com/portrait.jpg" alt="portrait">
    <p>John Doe is an abstract painter.</p></body></html>"""

    fetch_result = FetchResult(
        url="https://example.com/artists/john",
        final_url="https://example.com/artists/john",
        html=sample_html,
        status_code=200,
        method="httpx",
    )

    site_map = SiteMap(
        root_url="https://example.com",
        sections=[
            Section(
                name="Artists",
                url="https://example.com/artists/john",
                content_type="artist_directory",
                confidence=80,
            )
        ],
    )

    # Mock AI responses
    classify_result = ClassifyResult(
        page_type="artist_profile", confidence=90, reasoning="JSON-LD Person"
    )
    extract_data = {
        "name": "John Doe",
        "bio": "Abstract painter from Johannesburg.",
        "nationality": "South African",
        "birth_year": 1975,
        "mediums": ["oil"],
        "collections": [],
        "website_url": None,
        "instagram_url": None,
        "email": None,
        "avatar_url": "https://example.com/portrait.jpg",
        "image_urls": ["https://example.com/portrait.jpg"],
    }

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)

    with patch("app.pipeline.runner.map_site", new=AsyncMock(return_value=site_map)):
        with patch("app.crawler.link_follower.fetch", new=AsyncMock(return_value=fetch_result)):
            with patch.object(
                runner.robots_checker, "is_allowed", new=AsyncMock(return_value=True)
            ):
                with patch("app.pipeline.runner.classify_page", new=AsyncMock(return_value=classify_result)):
                    with patch.object(
                        runner._extractors["artist"], "extract", new=AsyncMock(return_value=extract_data)
                    ):
                        with patch("app.pipeline.runner.collect_images", new=AsyncMock(return_value=[])):
                            await runner.run_full_pipeline(source.id)

    updated_source = await crud.get_source(db_session, source.id)
    assert updated_source.status == "done"
    records = await crud.list_records(db_session, source_id=source.id, limit=10)
    assert len(records) == 1
    assert records[0].record_type == "artist"


@pytest.mark.asyncio
async def test_full_pipeline_runs_extraction_even_if_crawl_fails(
    db_session: AsyncSession, mock_ai_client
):
    from app.crawler.site_mapper import SiteMap
    from app.pipeline.runner import PipelineRunner

    source = await crud.create_source(
        db_session, url="https://crawl-fail.com", name="CrawlFail"
    )
    site_map = SiteMap(root_url="https://crawl-fail.com", sections=[])

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)
    with patch.object(runner, "run_map_site", new=AsyncMock(return_value=site_map)):
        with patch.object(runner, "run_crawl", new=AsyncMock(side_effect=RuntimeError("boom"))):
            extract_mock = AsyncMock()
            with patch.object(runner, "run_extract", new=extract_mock):
                with pytest.raises(RuntimeError, match="crawl failed before extraction"):
                    await runner.run_full_pipeline(source.id)

    assert extract_mock.await_count == 1


@pytest.mark.asyncio
async def test_full_pipeline_logs_extraction_started_after_slow_crawl_timeout(
    db_session: AsyncSession, mock_ai_client
):
    from app.crawler.site_mapper import SiteMap
    from app.pipeline.runner import PipelineRunner

    source = await crud.create_source(
        db_session, url="https://slow-timeout.com", name="Slow Timeout"
    )
    site_map = SiteMap(root_url="https://slow-timeout.com", sections=[])

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)

    async def _slow_crawl(*args, **kwargs):
        del args, kwargs
        await asyncio.sleep(0.01)
        raise TimeoutError("crawl exceeded timeout window")

    with patch.object(runner, "run_map_site", new=AsyncMock(return_value=site_map)):
        with patch.object(runner, "run_crawl", new=AsyncMock(side_effect=_slow_crawl)):
            with patch("app.pipeline.runner.logger") as mock_logger:
                with pytest.raises(RuntimeError, match="crawl failed before extraction"):
                    await runner.run_full_pipeline(source.id)

    extraction_logs = [
        call
        for call in mock_logger.info.call_args_list
        if call.args and call.args[0] == "extraction_started"
    ]
    assert len(extraction_logs) == 1
    assert extraction_logs[0].kwargs["source_id"] == source.id


@pytest.mark.asyncio
async def test_rerun_extract_does_not_duplicate_records(db_session: AsyncSession, mock_ai_client):
    from app.ai.classifier import ClassifyResult
    from app.pipeline.runner import PipelineRunner

    source = await crud.create_source(db_session, url="https://idempotent.com", name="Idempotent")
    page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://idempotent.com/artist/jane",
        original_url="https://idempotent.com/artist/jane",
        status="fetched",
        html="<html><body><h1>Jane</h1></body></html>",
    )

    classify_result = ClassifyResult(
        page_type="artist_profile", confidence=90, reasoning="URL pattern"
    )
    extract_data = {
        "name": "Jane",
        "bio": "Painter",
        "mediums": ["oil"],
        "collections": [],
        "image_urls": [],
    }

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)
    with patch("app.pipeline.runner.classify_page", new=AsyncMock(return_value=classify_result)):
        with patch.object(runner._extractors["artist"], "extract", new=AsyncMock(return_value=extract_data)):
            with patch("app.pipeline.runner.collect_images", new=AsyncMock(return_value=[])):
                await runner.run_extract(source.id)
                await crud.update_page(db_session, page.id, status="fetched")
                await runner.run_extract(source.id)

    records = await crud.list_records(db_session, source_id=source.id, limit=10)
    assert len(records) == 1


@pytest.mark.asyncio
async def test_extract_only_processes_eligible_pages(db_session: AsyncSession, mock_ai_client):
    from app.ai.classifier import ClassifyResult
    from app.pipeline.runner import PipelineRunner

    source = await crud.create_source(db_session, url="https://eligibility.com")
    extracted_page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://eligibility.com/artist/done",
        original_url="https://eligibility.com/artist/done",
        status="extracted",
        html="<html><body>Done</body></html>",
    )
    fetched_page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://eligibility.com/artist/new",
        original_url="https://eligibility.com/artist/new",
        status="fetched",
        html="<html><body>New</body></html>",
    )

    classify_result = ClassifyResult(
        page_type="artist_profile", confidence=80, reasoning="URL pattern"
    )
    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)
    classify_mock = AsyncMock(return_value=classify_result)
    with patch("app.pipeline.runner.classify_page", new=classify_mock):
        with patch.object(
            runner._extractors["artist"],
            "extract",
            new=AsyncMock(return_value={"name": "New", "bio": "Bio", "image_urls": []}),
        ):
            with patch("app.pipeline.runner.collect_images", new=AsyncMock(return_value=[])):
                await runner.run_extract(source.id)

    assert classify_mock.await_count == 1
    refreshed_extracted = await crud.get_page(db_session, extracted_page.id)
    refreshed_fetched = await crud.get_page(db_session, fetched_page.id)
    assert refreshed_extracted.status == "extracted"
    assert refreshed_fetched.status == "extracted"


@pytest.mark.asyncio
async def test_crawl_preserves_terminal_page_statuses(db_session: AsyncSession):
    from app.crawler.fetcher import FetchResult
    from app.crawler.link_follower import crawl_source
    from app.crawler.site_mapper import SiteMap

    source = await crud.create_source(db_session, url="https://crawl-preserve.com")
    page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://crawl-preserve.com/artist/jane",
        original_url="https://crawl-preserve.com/artist/jane",
        status="extracted",
        html="<html><head><title>Old</title></head><body>Old</body></html>",
    )
    site_map = SiteMap(root_url=source.url, sections=[])
    fetch_result = FetchResult(
        url=page.url,
        final_url=page.url,
        html="<html><head><title>New</title></head><body>New</body></html>",
        status_code=200,
        method="httpx",
    )

    robots_checker = MagicMock()
    robots_checker.is_allowed = AsyncMock(return_value=True)

    with patch("app.crawler.link_follower.fetch", new=AsyncMock(return_value=fetch_result)):
        await crawl_source(
            source_id=source.id,
            site_map=site_map,
            db=db_session,
            robots_checker=robots_checker,
            max_pages=1,
            max_depth=0,
        )

    refreshed_page = await crud.get_page(db_session, page.id)
    assert refreshed_page is not None
    assert refreshed_page.status == "extracted"


@pytest.mark.asyncio
async def test_pipeline_handles_fetch_error(db_session: AsyncSession, mock_ai_client):
    from app.crawler.fetcher import FetchResult
    from app.crawler.site_mapper import Section, SiteMap
    from app.pipeline.runner import PipelineRunner

    source = await crud.create_source(db_session, url="https://errsite.com")
    await crud.update_source(
        db_session,
        source.id,
        structure_map=json.dumps(
            {
                "crawl_plan": {"phases": []},
                "extraction_rules": {},
                "directory_structure": "test",
            }
        ),
    )
    site_map = SiteMap(root_url="https://errsite.com", sections=[])

    error_result = FetchResult(
        url="https://errsite.com",
        final_url="https://errsite.com",
        html="",
        status_code=0,
        method="httpx",
        error="Connection refused",
    )

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)
    with patch("app.pipeline.runner.map_site", new=AsyncMock(return_value=site_map)):
        with patch("app.crawler.link_follower.fetch", new=AsyncMock(return_value=error_result)):
            with patch.object(
                runner.robots_checker, "is_allowed", new=AsyncMock(return_value=True)
            ):
                # Pipeline should complete even with fetch errors
                await runner.run_full_pipeline(source.id)

    updated = await crud.get_source(db_session, source.id)
    assert updated.status in ("done", "error")


@pytest.mark.asyncio
async def test_pipeline_handles_ai_error(db_session: AsyncSession, mock_ai_client):
    from app.ai.classifier import ClassifyResult
    from app.ai.client import AIExtractionError
    from app.crawler.fetcher import FetchResult
    from app.crawler.site_mapper import Section, SiteMap
    from app.pipeline.runner import PipelineRunner

    source = await crud.create_source(db_session, url="https://aierr.com")
    html = "<html><body><h1>Artist Page</h1></body></html>"

    # Create a fetched page
    page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://aierr.com/artist/john",
        original_url="https://aierr.com/artist/john",
        status="fetched",
        html=html,
    )

    classify_result = ClassifyResult(
        page_type="artist_profile", confidence=80, reasoning="URL pattern"
    )

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)

    # AI extraction raises error
    with patch("app.pipeline.runner.classify_page", new=AsyncMock(return_value=classify_result)):
        with patch.object(
            runner._extractors["artist"],
            "extract",
            new=AsyncMock(side_effect=AIExtractionError("API error")),
        ):
            # Should not crash
            result = await runner.run_extraction_for_page(page)

    assert result is None


@pytest.mark.asyncio
async def test_crawl_hints_page_role_override_and_same_slug_override(
    db_session: AsyncSession, mock_ai_client
):
    from app.pipeline.runner import PipelineRunner

    crawl_hints = {
        "page_role_overrides": {"https://hints.com/alice/": "artist_profile_hub"},
        "same_slug_children": ["bio.php"],
    }
    source = await crud.create_source(
        db_session,
        url="https://hints.com",
        crawl_hints=json.dumps(crawl_hints),
    )
    await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://hints.com/alice/",
        original_url="https://hints.com/alice/",
        status="fetched",
        html="<html><body><h1>Alice</h1></body></html>",
    )

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)
    with patch("app.pipeline.runner.fetch", new=AsyncMock()) as fetch_mock:
        fetch_mock.return_value = type(
            "FetchResult",
            (),
            {
                "error": None,
                "url": "https://hints.com/alice/bio.php",
                "final_url": "https://hints.com/alice/bio.php",
                "html": "<html><body>Bio page</body></html>",
                "method": "httpx",
            },
        )()
        with patch.object(
            runner._extractors["artist"],
            "extract",
            new=AsyncMock(return_value={"name": "Alice", "bio": "Bio", "image_urls": []}),
        ):
            await runner.run_extract(source.id)

    child, _ = await crud.get_or_create_page(db_session, source.id, "https://hints.com/alice/bio.php")
    assert child.url.endswith("bio.php")


@pytest.mark.asyncio
async def test_force_deepen_and_ignore_patterns(db_session: AsyncSession, mock_ai_client):
    from app.pipeline.runner import PipelineRunner

    crawl_hints = {
        "force_deepen_urls": ["https://force.com/alice/"],
        "ignore_url_patterns": ["/login"],
    }
    source = await crud.create_source(
        db_session,
        url="https://force.com",
        crawl_hints=json.dumps(crawl_hints),
    )
    await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://force.com/login",
        original_url="https://force.com/login",
        status="fetched",
        html="<html><body>login</body></html>",
    )
    await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://force.com/alice/",
        original_url="https://force.com/alice/",
        status="fetched",
        html="<html><body>Artist</body></html>",
    )

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)
    with patch("app.pipeline.runner.fetch", new=AsyncMock()) as fetch_mock:
        fetch_mock.return_value = type(
            "FetchResult",
            (),
            {
                "error": "404",
                "url": "https://force.com/alice/about.php",
                "final_url": "https://force.com/alice/about.php",
                "html": "",
                "method": "httpx",
            },
        )()
        with patch("app.pipeline.runner.classify_page", new=AsyncMock(return_value=type(
            "ClassifyResult", (), {"page_type": "unknown", "confidence": 0, "reasoning": "test"}
        )())):
            with patch.object(
                runner._extractors["artist"],
                "extract",
                new=AsyncMock(return_value={"name": "Alice", "bio": "Bio", "image_urls": []}),
            ):
                await runner.run_extract(source.id)

    pages = await crud.list_pages(db_session, source_id=source.id, limit=50)
    urls = {p.url for p in pages}
    assert "https://force.com/alice/about.php" in urls
    login_page = [p for p in pages if p.url.endswith("/login")][0]
    assert login_page.status == "skipped"


@pytest.mark.asyncio
async def test_artist_related_records_are_idempotent(db_session: AsyncSession, mock_ai_client):
    from app.ai.classifier import ClassifyResult
    from app.pipeline.runner import PipelineRunner

    source = await crud.create_source(db_session, url="https://repeat.com")
    page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://repeat.com/alice/exhibitions.php",
        original_url="https://repeat.com/alice/exhibitions.php",
        status="fetched",
        html="""
        <ul><li><strong>Solo Show</strong>, Gallery, 2019</li></ul>
        """,
    )

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)
    with patch(
        "app.pipeline.runner.classify_page",
        new=AsyncMock(
            return_value=ClassifyResult(page_type="artist_exhibitions", confidence=90, reasoning="test")
        ),
    ):
        await runner.run_extract(source.id)
        await crud.update_page(db_session, page.id, status="fetched")
        await runner.run_extract(source.id)

    records = await crud.list_records(db_session, source_id=source.id, limit=50)
    exhibition_children = [r for r in records if r.record_type == "exhibition"]
    assert len(exhibition_children) == 1


@pytest.mark.asyncio
@respx.mock
async def test_image_collection(db_session: AsyncSession):
    from app.pipeline.image_collector import collect_images

    source = await crud.create_source(db_session, url="https://imgtest.com")
    record = await crud.create_record(
        db_session, source_id=source.id, record_type="artist", title="Test Artist"
    )

    html = """<html><body>
    <img src="https://imgtest.com/portrait.jpg" alt="portrait" width="400" height="400">
    <img src="https://imgtest.com/artwork.jpg" alt="artwork painting" width="800" height="600">
    </body></html>"""

    respx.head("https://imgtest.com/portrait.jpg").mock(
        return_value=Response(200, headers={"content-type": "image/jpeg"})
    )
    respx.head("https://imgtest.com/artwork.jpg").mock(
        return_value=Response(200, headers={"content-type": "image/jpeg"})
    )

    images = await collect_images(
        record_id=record.id,
        page_url="https://imgtest.com/artist/john",
        html=html,
        image_urls=[],
        db=db_session,
        source_id=source.id,
    )

    assert len(images) >= 1
    types = {img.image_type for img in images}
    assert "profile" in types or "artwork" in types or "unknown" in types


@pytest.mark.asyncio
async def test_discovery_hub_deepens_child_pages(db_session: AsyncSession, mock_ai_client):
    from app.ai.classifier import ClassifyResult
    from app.crawler.fetcher import FetchResult
    from app.pipeline.runner import PipelineRunner

    source = await crud.create_source(db_session, url="https://example.com")
    hub_page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://example.com/aliceelahi/",
        original_url="https://example.com/aliceelahi/",
        status="fetched",
        html="<html><body><h1>Alice Elahi</h1></body></html>",
    )

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)
    classify_result = ClassifyResult(
        page_type="artist_profile_hub",
        confidence=85,
        reasoning="hub nav links detected",
    )

    async def _mock_fetch(url: str):
        return FetchResult(
            url=url,
            final_url=url,
            html=f"<html><body><h1>{url}</h1></body></html>",
            status_code=200,
            method="httpx",
        )

    with patch("app.pipeline.runner.classify_page", new=AsyncMock(return_value=classify_result)):
        with patch("app.pipeline.runner.fetch", new=AsyncMock(side_effect=_mock_fetch)):
            await runner.run_extraction_for_page(hub_page)

    refreshed_hub = await crud.get_page(db_session, hub_page.id)
    assert refreshed_hub is not None
    assert refreshed_hub.status == "expanded"

    child_paths = [
        "about.php",
        "exhibitions.php",
        "articles.php",
        "press.php",
        "memories.php",
    ]
    for child_path in child_paths:
        child_url = f"https://example.com/aliceelahi/{child_path}"
        result = await db_session.execute(
            select(Page).where(Page.source_id == source.id, Page.url == child_url)
        )
        child_page = result.scalar_one_or_none()
        assert child_page is not None
        assert child_page.status == "fetched"
        assert child_page.html is not None


@pytest.mark.asyncio
async def test_classify_page_with_structure_uses_pattern_without_ai(db_session: AsyncSession, mock_ai_client):
    from app.pipeline.runner import PipelineRunner

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)
    structure_map = {
        "mining_map": {
            "artist_profile": {
                "url_pattern": "/artists/[letter]/[name]",
                "expected_fields": ["name", "bio"],
            }
        }
    }

    result = runner.classify_page_with_structure(
        "https://example.com/artists/a/john-doe", structure_map
    )
    assert result is not None
    assert result["page_type"] == "artist_profile"
    assert result["expected_fields"] == ["name", "bio"]


@pytest.mark.asyncio
async def test_matches_pattern_url_tokens(db_session: AsyncSession, mock_ai_client):
    from app.pipeline.runner import PipelineRunner

    runner = PipelineRunner(db=db_session, ai_client=mock_ai_client)
    assert runner._matches_pattern_url("https://example.com/artists/b/jane", "/artists/[letter]/[name]")
    assert runner._matches_pattern_url("https://example.com/artworks/123", "/artworks/[id]")
    assert not runner._matches_pattern_url("https://example.com/artists/jane", "/artists/[letter]/[name]")
