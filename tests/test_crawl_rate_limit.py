from unittest.mock import AsyncMock, patch

import pytest

from app.crawler.fetcher import FetchResult
from app.crawler.durable_frontier import run_durable_crawl
from app.db import crud


@pytest.mark.asyncio
async def test_rate_limited_frontier_row_becomes_retryable(db_session):
    source = await crud.create_source(db_session, url="https://rate-limit.test")

    with patch(
        "app.crawler.durable_frontier.fetch",
        new=AsyncMock(
            return_value=FetchResult(
                url=source.url,
                final_url=source.url,
                html="",
                status_code=429,
                method="httpx",
                error=None,
            )
        ),
    ):
        stats = await run_durable_crawl(
            db_session,
            source_id=source.id,
            seed_url=source.url,
            job_id=None,
            worker_id="worker-1",
            max_pages=1,
            max_depth=1,
        )

    assert stats["rate_limited"] >= 1
    crawl_run = await crud.get_active_crawl_run_for_source(db_session, source.id)
    assert crawl_run is not None
    assert crawl_run.status in {"cooling_down", "running", "completed"}


@pytest.mark.asyncio
async def test_durable_crawl_skips_robots_blocked_urls_without_fetch(db_session):
    source = await crud.create_source(db_session, url="https://robots-blocked.test")
    robots_checker = AsyncMock()
    robots_checker.is_allowed = AsyncMock(return_value=False)
    fetch_mock = AsyncMock(
        return_value=FetchResult(
            url=source.url,
            final_url=source.url,
            html="<html></html>",
            status_code=200,
            method="httpx",
        )
    )

    with patch("app.crawler.durable_frontier.fetch", new=fetch_mock):
        stats = await run_durable_crawl(
            db_session,
            source_id=source.id,
            seed_url=source.url,
            job_id=None,
            worker_id="worker-1",
            max_pages=1,
            max_depth=1,
            robots_checker=robots_checker,
        )

    assert fetch_mock.await_count == 0
    assert stats["robots_blocked"] == 1
    crawl_run = await crud.get_active_crawl_run_for_source(db_session, source.id)
    counts = await crud.get_crawl_frontier_counts(db_session, crawl_run.id)
    assert counts.get("skipped", 0) == 1


@pytest.mark.asyncio
async def test_durable_crawl_fetches_allowed_urls(db_session):
    source = await crud.create_source(db_session, url="https://robots-allowed.test")
    robots_checker = AsyncMock()
    robots_checker.is_allowed = AsyncMock(return_value=True)
    fetch_mock = AsyncMock(
        return_value=FetchResult(
            url=source.url,
            final_url=source.url,
            html="<html><body><a href='/next'>next</a></body></html>",
            status_code=200,
            method="httpx",
        )
    )

    with patch("app.crawler.durable_frontier.fetch", new=fetch_mock):
        stats = await run_durable_crawl(
            db_session,
            source_id=source.id,
            seed_url=source.url,
            job_id=None,
            worker_id="worker-1",
            max_pages=1,
            max_depth=1,
            robots_checker=robots_checker,
        )

    assert fetch_mock.await_count == 1
    assert stats["pages_crawled"] >= 1
    assert stats["robots_blocked"] == 0


@pytest.mark.asyncio
async def test_robots_blocked_row_is_not_retryable(db_session):
    source = await crud.create_source(db_session, url="https://robots-no-retry.test")
    robots_checker = AsyncMock()
    robots_checker.is_allowed = AsyncMock(return_value=False)

    with patch("app.crawler.durable_frontier.fetch", new=AsyncMock()):
        await run_durable_crawl(
            db_session,
            source_id=source.id,
            seed_url=source.url,
            job_id=None,
            worker_id="worker-1",
            max_pages=1,
            max_depth=1,
            robots_checker=robots_checker,
        )

    crawl_run = await crud.get_active_crawl_run_for_source(db_session, source.id)
    claimed = await crud.claim_frontier_rows(
        db_session,
        crawl_run_id=crawl_run.id,
        worker_id="worker-2",
        limit=10,
        lease_seconds=30,
    )
    assert claimed == []
