from __future__ import annotations

import asyncio
import json
import os
import socket
from datetime import UTC, datetime
from typing import Any

import structlog
from bs4 import BeautifulSoup
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.fetcher import fetch
from app.db.database import AsyncSessionLocal
from app.db.log_writer import log_stream_manager
from app.db.models import BackfillCampaign, BackfillJob, Page, Record
from app.queue import QueueUnavailableError, get_default_queue
from app.services.completeness import calculate_completeness, update_record_completeness

logger = structlog.get_logger()
BACKFILL_JOB_TIMEOUT_SECONDS = 600
WORKER_ID = os.environ.get("WORKER_ID", f"{socket.gethostname()}-{os.getpid()}")


async def _emit_backfill_progress(
    *,
    backfill_job_id: str,
    source_id: str,
    stage: str,
    message: str,
    item: str | None = None,
    level: str = "info",
    event_type: str = "progress",
    progress_current: int | None = None,
    progress_total: int | None = None,
) -> None:
    await log_stream_manager.publish(
        {
            "stream_type": "job_progress",
            "job_id": backfill_job_id,
            "worker_id": WORKER_ID,
            "source_id": source_id,
            "stage": stage,
            "message": message,
            "event_type": event_type,
            "level": level,
            "item": item,
            "progress_current": progress_current,
            "progress_total": progress_total,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


async def _control_checkpoint(job: BackfillJob) -> None:
    while True:
        if job.status == "cancelled":
            raise RuntimeError("Backfill job cancelled by operator")
        if job.status != "paused":
            return
        await asyncio.sleep(1)


async def enqueue_backfill_campaign(db: AsyncSession, campaign_id: str) -> int:
    """Enqueue all pending jobs for a campaign to RQ."""
    queue = get_default_queue()

    campaign = await db.get(BackfillCampaign, campaign_id)
    if campaign is None:
        raise ValueError(f"Campaign {campaign_id} not found")

    result = await db.execute(
        select(BackfillJob).where(
            BackfillJob.campaign_id == campaign_id,
            BackfillJob.status == "pending",
        )
    )
    jobs = result.scalars().all()

    campaign.status = "running"
    if campaign.started_at is None:
        campaign.started_at = datetime.now(UTC)

    enqueued = 0
    for job in jobs:
        rq_job = queue.enqueue(
            "app.pipeline.backfill_processor.process_backfill_job",
            job.id,
            job_timeout=BACKFILL_JOB_TIMEOUT_SECONDS,
            failure_ttl=86400,
        )
        job.status = "queued"
        enqueued += 1
        logger.info(
            "backfill_job_enqueued",
            campaign_id=campaign_id,
            backfill_job_id=job.id,
            rq_job_id=rq_job.id,
        )

    await db.commit()
    logger.info("backfill_campaign_enqueued", campaign_id=campaign_id, jobs_enqueued=enqueued)
    return enqueued


def process_backfill_job(job_id: str) -> None:
    """RQ entrypoint to process a single backfill job."""
    asyncio.run(_process_backfill_job_async(job_id))


async def _process_backfill_job_async(job_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(BackfillJob).where(BackfillJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            logger.warning("backfill_job_missing", backfill_job_id=job_id)
            return

        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.attempts += 1
        await db.commit()

        try:
            await db.refresh(job)
            await _control_checkpoint(job)
            record = await db.get(Record, job.record_id)
            if record is None:
                raise ValueError(f"Record {job.record_id} not found")
            await _emit_backfill_progress(
                backfill_job_id=job.id,
                source_id=record.source_id,
                stage="backfill_fetch",
                item=job.url_to_crawl,
                message="Backfill record job started",
                event_type="job_started",
            )

            before = job.before_completeness
            if before is None:
                before = calculate_completeness(record)["score"]

            html = await _get_or_fetch_page_html(db, job.url_to_crawl, record.source_id)
            await _emit_backfill_progress(
                backfill_job_id=job.id,
                source_id=record.source_id,
                stage="backfill_extract",
                item=job.url_to_crawl,
                message="Extracting missing fields",
                progress_current=1,
                progress_total=3,
            )
            extracted_data = _extract_record_data(html, record.record_type)
            await _emit_backfill_progress(
                backfill_job_id=job.id,
                source_id=record.source_id,
                stage="backfill_merge",
                item=record.id,
                message="Merging extracted fields into record",
                progress_current=2,
                progress_total=3,
            )
            updated_fields = _merge_data_into_record(record, extracted_data)

            after_data = await update_record_completeness(db, record)
            after = after_data["score"]

            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            job.after_completeness = after
            job.fields_updated = json.dumps(updated_fields)
            job.error_message = None

            await _update_campaign_stats(db, job.campaign_id, success=True)
            await db.commit()

            logger.info(
                "backfill_job_completed",
                backfill_job_id=job_id,
                record_id=record.id,
                record_type=record.record_type,
                before_completeness=before,
                after_completeness=after,
                improvement=after - before,
                fields_updated=updated_fields,
            )
            await _emit_backfill_progress(
                backfill_job_id=job.id,
                source_id=record.source_id,
                stage="finalizing",
                item=record.id,
                message="Backfill record completed",
                event_type="job_completed",
                progress_current=3,
                progress_total=3,
            )
        except Exception as exc:
            logger.exception("backfill_job_failed", backfill_job_id=job_id, error=str(exc))
            job.status = "failed"
            job.completed_at = datetime.now(UTC)
            job.error_message = str(exc)
            await _update_campaign_stats(db, job.campaign_id, success=False)
            await db.commit()
            source_id = record.source_id if "record" in locals() and record is not None else "unknown"
            await _emit_backfill_progress(
                backfill_job_id=job.id,
                source_id=source_id,
                stage="finalizing",
                item=job.record_id,
                message=f"Backfill record failed: {exc}",
                level="error",
                event_type="job_failed",
            )
            raise


async def _get_or_fetch_page_html(db: AsyncSession, url: str, source_id: str) -> str:
    existing = (
        (
            await db.execute(
                select(Page).where(
                    Page.source_id == source_id,
                    Page.url == url,
                    Page.html.is_not(None),
                )
            )
        )
        .scalars()
        .first()
    )
    if existing and existing.html:
        logger.info("backfill_page_cache_hit", source_id=source_id, url=url, page_id=existing.id)
        return existing.html

    fetched = await fetch(url)
    if fetched.error or not fetched.html:
        raise RuntimeError(f"Fetch failed for {url}: {fetched.error or 'empty html'}")

    page = Page(
        source_id=source_id,
        url=url,
        original_url=fetched.final_url,
        page_type="backfill",
        status="fetched",
        depth=0,
        fetch_method=fetched.method,
        html=fetched.html,
        crawled_at=datetime.now(UTC),
    )
    db.add(page)
    await db.flush()
    logger.info("backfill_page_fetched", source_id=source_id, url=url, page_id=page.id, fetch_method=fetched.method)
    return fetched.html


def _extract_record_data(html: str, record_type: str) -> dict[str, Any]:
    """Best-effort fallback extraction for backfill records."""
    soup = BeautifulSoup(html, "html.parser")
    data: dict[str, Any] = {}

    if record_type == "artist":
        bio_selectors = [
            "div.biography",
            "div.bio",
            "section.biography",
            "section.bio",
            "article .bio",
            "p.biography",
        ]
        for selector in bio_selectors:
            elem = soup.select_one(selector)
            if elem:
                bio = elem.get_text(" ", strip=True)
                if bio:
                    data["bio"] = bio[:1000]
                    break

        for link in soup.select("a[href]"):
            href = (link.get("href") or "").strip()
            text = link.get_text(" ", strip=True).lower()
            if not href:
                continue
            if "instagram.com" in href and not data.get("instagram_url"):
                data["instagram_url"] = href
            if ("website" in text or "portfolio" in text) and not data.get("website_url"):
                data["website_url"] = href

    elif record_type in {"event", "exhibition"}:
        for selector in [".description", "article p", "main p"]:
            elem = soup.select_one(selector)
            if elem:
                description = elem.get_text(" ", strip=True)
                if description:
                    data["description"] = description[:2000]
                    break

    elif record_type == "venue":
        for selector in [".address", "address", "[itemprop='address']"]:
            elem = soup.select_one(selector)
            if elem:
                address = elem.get_text(" ", strip=True)
                if address:
                    data["address"] = address[:500]
                    break

    return data


def _merge_data_into_record(record: Record, extracted_data: dict[str, Any]) -> list[str]:
    updated: list[str] = []
    for field, value in extracted_data.items():
        if value in (None, "", "[]", "{}"):
            continue
        current = getattr(record, field, None)
        if current in (None, "", "[]", "{}"):
            setattr(record, field, value)
            updated.append(field)
    return updated


async def _update_campaign_stats(db: AsyncSession, campaign_id: str, success: bool) -> None:
    campaign = await db.get(BackfillCampaign, campaign_id)
    if campaign is None:
        return

    campaign.processed_records += 1
    if success:
        campaign.successful_updates += 1
    else:
        campaign.failed_updates += 1

    if campaign.processed_records >= campaign.total_records:
        campaign.status = "completed"
        campaign.completed_at = datetime.now(UTC)

    await db.flush()


async def check_campaign_completion(db: AsyncSession, campaign_id: str) -> dict[str, int]:
    campaign = await db.get(BackfillCampaign, campaign_id)
    if campaign is None:
        raise ValueError(f"Campaign {campaign_id} not found")

    result = await db.execute(select(BackfillJob).where(BackfillJob.campaign_id == campaign_id))
    jobs = result.scalars().all()
    pending = sum(1 for j in jobs if j.status in {"pending", "queued", "running"})
    completed = sum(1 for j in jobs if j.status == "completed")
    failed = sum(1 for j in jobs if j.status == "failed")

    if pending == 0 and campaign.status == "running":
        campaign.status = "completed"
        campaign.completed_at = datetime.now(UTC)
        campaign.processed_records = completed + failed
        campaign.successful_updates = completed
        campaign.failed_updates = failed
        await db.commit()

    return {"pending": pending, "completed": completed, "failed": failed}


__all__ = [
    "enqueue_backfill_campaign",
    "process_backfill_job",
    "check_campaign_completion",
]
