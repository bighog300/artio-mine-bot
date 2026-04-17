from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.fetcher import fetch
from app.crawler.url_utils import normalize_url
from app.db import crud
from app.pipeline.job_progress import report_job_progress

logger = structlog.get_logger()
RETRYABLE_STATUS_CODES = {429, 503}


def _extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html or "", "lxml")
    items: list[str] = []
    base_domain = urlparse(base_url).netloc
    for node in soup.find_all("a", href=True):
        href = (node.get("href") or "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        full = urljoin(base_url, href).split("#")[0]
        if urlparse(full).netloc != base_domain:
            continue
        items.append(full)
    return items


def _parse_retry_after_seconds(retry_after: str | None) -> int:
    if not retry_after:
        return 30
    try:
        return max(1, int(retry_after))
    except ValueError:
        return 30


async def _emit_crawl_event(
    db: AsyncSession,
    *,
    job_id: str | None,
    source_id: str,
    crawl_run_id: str,
    worker_id: str | None,
    event_type: str,
    message: str,
    level: str = "info",
    context: dict[str, Any] | None = None,
) -> None:
    if job_id:
        await crud.append_job_event(
            db,
            job_id=job_id,
            source_id=source_id,
            worker_id=worker_id,
            event_type=event_type,
            message=message,
            level=level,
            stage="crawling",
            context={"crawl_run_id": crawl_run_id, **(context or {})},
        )
    if job_id:
        await report_job_progress(
            db,
            job_id,
            source_id=source_id,
            stage="crawling",
            message=message,
            event_type=event_type,
            metrics={"crawl_run_id": crawl_run_id, **(context or {})},
            worker_id=worker_id,
            level=level,
        )


async def run_durable_crawl(
    db: AsyncSession,
    *,
    source_id: str,
    seed_url: str,
    job_id: str | None,
    worker_id: str,
    max_pages: int,
    max_depth: int,
) -> dict[str, Any]:
    crawl_run = await crud.get_active_crawl_run_for_source(db, source_id)
    if crawl_run is None or crawl_run.status in {"completed", "failed", "cancelled"}:
        crawl_run = await crud.create_crawl_run(
            db,
            source_id=source_id,
            seed_url=seed_url,
            job_id=job_id,
            status="running",
            worker_id=worker_id,
        )
        await crud.upsert_crawl_frontier_rows(
            db,
            crawl_run_id=crawl_run.id,
            source_id=source_id,
            rows=[
                {
                    "url": seed_url,
                    "normalized_url": normalize_url(seed_url),
                    "depth": 0,
                    "status": "queued",
                }
            ],
        )
    else:
        crawl_run = await crud.update_crawl_run(
            db,
            crawl_run.id,
            status="running",
            worker_id=worker_id,
            started_at=crawl_run.started_at or datetime.now(UTC),
            job_id=job_id or crawl_run.job_id,
        )

    processed = 0
    while processed < max_pages:
        source = await crud.get_source(db, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")
        if source.queue_paused or crawl_run.status == "paused":
            await crud.update_crawl_run(db, crawl_run.id, status="paused", last_heartbeat_at=datetime.now(UTC))
            await _emit_crawl_event(
                db,
                job_id=job_id,
                source_id=source_id,
                crawl_run_id=crawl_run.id,
                worker_id=worker_id,
                event_type="crawl_paused",
                message="Crawl paused by source or crawl-run control",
            )
            break
        if crawl_run.status == "cancelled":
            break

        await crud.reclaim_expired_frontier_leases(db, crawl_run_id=crawl_run.id)
        batch = await crud.claim_frontier_rows(
            db,
            crawl_run_id=crawl_run.id,
            worker_id=worker_id,
            limit=10,
            lease_seconds=120,
        )
        if not batch:
            counts = await crud.get_crawl_frontier_counts(db, crawl_run.id)
            queued = counts.get("queued", 0) + counts.get("leased", 0) + counts.get("rate_limited", 0)
            if queued <= 0:
                await crud.update_crawl_run(
                    db,
                    crawl_run.id,
                    status="completed",
                    completed_at=datetime.now(UTC),
                    last_heartbeat_at=datetime.now(UTC),
                    stats_json=json.dumps(counts),
                )
            break

        for row in batch:
            if row.depth > max_depth:
                await crud.update_frontier_row(db, row.id, status="skipped", last_error="max_depth_exceeded")
                continue
            result = await fetch(row.url)
            now = datetime.now(UTC)
            if result.status_code in RETRYABLE_STATUS_CODES:
                retry_after_s = _parse_retry_after_seconds(None)
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status="rate_limited",
                    retry_count=int(row.retry_count or 0) + 1,
                    next_retry_at=now + timedelta(seconds=retry_after_s),
                    last_status_code=result.status_code,
                    last_error=f"rate_limited_{result.status_code}",
                )
                await crud.update_crawl_run(
                    db,
                    crawl_run.id,
                    status="cooling_down",
                    cooldown_until=now + timedelta(seconds=retry_after_s),
                    last_heartbeat_at=now,
                )
                await _emit_crawl_event(
                    db,
                    job_id=job_id,
                    source_id=source_id,
                    crawl_run_id=crawl_run.id,
                    worker_id=worker_id,
                    event_type="retry_scheduled",
                    message="Rate-limited URL scheduled for retry",
                    context={"url": row.url, "status_code": result.status_code, "retry_after_seconds": retry_after_s},
                )
                continue

            if result.error:
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status="error",
                    last_error=result.error,
                    last_status_code=result.status_code,
                )
                continue

            page, _created = await crud.get_or_create_page(db, source_id=source_id, url=result.final_url)
            await crud.update_page(
                db,
                page.id,
                crawl_run_id=crawl_run.id,
                original_url=row.url,
                status="fetched",
                depth=row.depth,
                fetch_method=result.method,
                html=(result.html or "").replace("\x00", "")[: 500 * 1024],
                title=(BeautifulSoup(result.html or "", "lxml").title.string.strip() if BeautifulSoup(result.html or "", "lxml").title and BeautifulSoup(result.html or "", "lxml").title.string else None),
                crawled_at=now,
            )
            await crud.update_frontier_row(
                db,
                row.id,
                status="fetched",
                last_status_code=result.status_code,
                last_fetched_at=now,
                lease_expires_at=None,
                leased_by_worker=None,
            )
            links = _extract_links(result.html or "", result.final_url)
            await crud.upsert_crawl_frontier_rows(
                db,
                crawl_run_id=crawl_run.id,
                source_id=source_id,
                rows=[
                    {
                        "url": link,
                        "normalized_url": normalize_url(link),
                        "depth": row.depth + 1,
                        "status": "queued",
                        "discovered_from_url": result.final_url,
                    }
                    for link in links
                ],
            )
            processed += 1
            await crud.update_crawl_run(
                db,
                crawl_run.id,
                status="running",
                last_heartbeat_at=now,
                cooldown_until=None,
            )
            await _emit_crawl_event(
                db,
                job_id=job_id,
                source_id=source_id,
                crawl_run_id=crawl_run.id,
                worker_id=worker_id,
                event_type="page_fetched",
                message="Page fetched",
                context={"url": result.final_url, "depth": row.depth},
            )

    counts = await crud.get_crawl_frontier_counts(db, crawl_run.id)
    return {
        "crawl_run_id": crawl_run.id,
        "pages_crawled": counts.get("fetched", 0),
        "failed": counts.get("error", 0),
        "queued": counts.get("queued", 0),
        "rate_limited": counts.get("rate_limited", 0),
    }
