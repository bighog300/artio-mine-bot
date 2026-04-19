import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.crawler.fetcher import FetchResult
from app.pipeline.runner import PipelineRunner
from app.runtime_ai_policy import RuntimeAIPolicyViolation, runtime_ai_policy
from app.db import crud


@pytest.mark.asyncio
async def test_runtime_policy_blocks_openai_calls():
    from app.ai.client import OpenAIClient

    client = OpenAIClient.__new__(OpenAIClient)
    mocked_response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
    )
    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=mocked_response)))
    )

    with pytest.raises(RuntimeAIPolicyViolation):
        with runtime_ai_policy(ai_allowed=False, mode="deterministic_runtime", reason="test"):
            await client.complete(system_prompt="x", user_content="y")


@pytest.mark.asyncio
async def test_published_runtime_skips_unchanged_pages_and_queues_review(db_session, monkeypatch):
    source = await crud.create_source(db_session, url="https://zero-ai.test", name="Zero AI")
    await crud.update_source(
        db_session,
        source.id,
        structure_map=json.dumps(
            {
                "crawl_targets": ["/artists/jane"],
                "extraction_rules": {"artist_profile": {"css_selectors": {"name": "h1"}, "identifiers": ["/artists/"]}},
            }
        ),
        published_mapping_version_id="map-v1",
        runtime_mode="deterministic_runtime",
        runtime_ai_enabled=False,
    )

    html = "<html><head><title>Jane</title></head><body><h1>Jane Doe</h1></body></html>"

    async def _fetch(_url: str):
        return FetchResult(
            url="https://zero-ai.test/artists/jane",
            final_url="https://zero-ai.test/artists/jane",
            html=html,
            status_code=200,
            method="httpx",
        )

    monkeypatch.setattr("app.crawler.automated_crawler.fetch", _fetch)

    runner = PipelineRunner(db=db_session, ai_client=None)
    first = await runner.run_deterministic_mine(source.id)
    second = await runner.run_deterministic_mine(source.id)

    pages = await crud.list_pages(db_session, source_id=source.id, limit=10)
    assert first["deterministic_hits"] == 1
    assert second["skipped_unchanged"] >= 1
    assert pages[0].review_reason is None


@pytest.mark.asyncio
async def test_published_runtime_unmapped_pages_are_reviewed_and_mark_stale(db_session, monkeypatch):
    source = await crud.create_source(db_session, url="https://drift.test", name="Drift")
    await crud.update_source(
        db_session,
        source.id,
        structure_map=json.dumps(
            {
                "crawl_targets": ["/unknown/1", "/unknown/2"],
                "extraction_rules": {"mapped_type": {"identifiers": ["/mapped/"], "css_selectors": {"title": "h1"}}},
            }
        ),
        published_mapping_version_id="map-v2",
        runtime_mode="deterministic_runtime",
        runtime_ai_enabled=False,
    )

    async def _fetch(url: str):
        return FetchResult(url=url, final_url=url, html="<html><body>No mapping</body></html>", status_code=200, method="httpx")

    monkeypatch.setattr("app.crawler.automated_crawler.fetch", _fetch)

    runner = PipelineRunner(db=db_session, ai_client=None)
    result = await runner.run_deterministic_mine(source.id)

    updated = await crud.get_source(db_session, source.id)
    pages = await crud.list_pages(db_session, source_id=source.id, limit=10)
    assert result["queued_for_review"] >= 2
    assert updated is not None and updated.mapping_stale is True
    assert all(page.review_status == "queued" for page in pages)
