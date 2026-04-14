import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response
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
