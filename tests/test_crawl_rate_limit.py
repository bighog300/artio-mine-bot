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
