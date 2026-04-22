from __future__ import annotations

import hashlib
import json
from asyncio import sleep
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.crawl_policy import score_url
from app.crawler.fetcher import fetch
from app.crawler.freshness import (
    compute_next_eligible_fetch_at,
    detect_content_change,
    normalize_freshness_policy,
)
from app.crawler.robots import RobotsChecker
from app.crawler.seeding import build_seed_rows
from app.crawler.url_utils import normalize_url
from app.db import crud
from app.pipeline.job_progress import report_job_progress

logger = structlog.get_logger()
RETRYABLE_STATUS_CODES = {429, 503}
TERMINAL_PAGE_STATUSES = {"completed", "extracted", "skipped", "expanded"}
CAPTCHA_MARKERS = (
    "captcha",
    "g-recaptcha",
    "hcaptcha",
    "cf-chl",
    "cloudflare challenge",
    "are you human",
)


class CrawlStage:
    """Explicit crawl processing stages used for observability and checkpointing."""

    QUEUED = "QUEUED"
    FETCHING = "FETCHING"
    PARSING = "PARSING"
    EXTRACTING = "EXTRACTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def _extract_links(html: str, base_url: str, source_domain: str) -> list[str]:
    """Extract same-domain links only and enforce source-domain boundary."""
    soup = BeautifulSoup(html or "", "lxml")
    items: list[str] = []
    base_domain = urlparse(base_url).netloc.lower()
    for node in soup.find_all("a", href=True):
        href = (node.get("href") or "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        full = urljoin(base_url, href).split("#")[0]
        link_domain = urlparse(full).netloc.lower()
        if link_domain != base_domain:
            continue
        if link_domain != source_domain:
            continue
        items.append(full)
    return items


def _parse_retry_after_seconds(retry_after: str | None, retry_count: int) -> int:
    """Exponential backoff with Retry-After override."""
    if retry_after:
        try:
            return max(1, int(retry_after))
        except ValueError:
            pass
    base = 10
    cap = 300
    return min(cap, base * (2 ** max(0, retry_count)))


def _is_captcha_page(html: str | None) -> bool:
    body = (html or "").lower()
    return any(marker in body for marker in CAPTCHA_MARKERS)


async def _emit_crawl_event(
    db: AsyncSession,
    *,
    job_id: str | None,
    source_id: str,
    crawl_run_id: str,
    worker_id: str | None,
    event_type: str,
    message: str,
    stage: str,
    url: str | None,
    level: str = "info",
    context: dict[str, Any] | None = None,
) -> None:
    event_context = {
        "source_id": source_id,
        "job_id": job_id,
        "worker_id": worker_id,
        "url": url,
        "stage": stage,
        "crawl_run_id": crawl_run_id,
        **(context or {}),
    }
    if job_id:
        await crud.append_job_event(
            db,
            job_id=job_id,
            source_id=source_id,
            worker_id=worker_id,
            event_type=event_type,
            message=message,
            level=level,
            stage=stage,
            context=event_context,
        )
    if job_id:
        await report_job_progress(
            db,
            job_id,
            source_id=source_id,
            stage=stage,
            message=message,
            event_type=event_type,
            metrics=event_context,
            worker_id=worker_id,
            level=level,
        )


async def _checkpoint(
    db: AsyncSession,
    *,
    crawl_run_id: str,
    source_id: str,
    mapping_version_id: str | None,
    status: str,
    processed: int,
    max_pages: int,
    worker_id: str,
    stage: str,
    last_processed_url: str | None = None,
) -> None:
    counts = await crud.get_crawl_frontier_counts(db, crawl_run_id)
    await crud.upsert_crawl_run_checkpoint(
        db,
        crawl_run_id=crawl_run_id,
        source_id=source_id,
        mapping_version_id=mapping_version_id,
        status=status,
        frontier_counts=counts,
        last_processed_url=last_processed_url,
        progress={"processed": processed, "max_pages": max_pages, "stage": stage},
        worker_state={"worker_id": worker_id, "stage": stage},
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
    robots_checker: RobotsChecker | None = None,
    refresh_mode: bool = False,
    force_refresh: bool = False,
    crawl_run_id: str | None = None,
) -> dict[str, Any]:
    """Run durable crawl with resume-safe frontier and strict idempotency guarantees."""
    robots_checker = robots_checker or RobotsChecker()
    source = await crud.get_source(db, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")

    resolved_seed_url = source.url or seed_url
    source_domain = urlparse(resolved_seed_url).netloc.lower()
    mapping_version_id = source.published_mapping_version_id
    crawl_run = await crud.get_crawl_run(db, crawl_run_id) if crawl_run_id else await crud.get_active_crawl_run_for_source(db, source_id)

    if crawl_run is None or crawl_run.status in {"completed", "failed", "cancelled"}:
        crawl_run = await crud.create_crawl_run(
            db,
            source_id=source_id,
            seed_url=resolved_seed_url,
            job_id=job_id,
            status="running",
            worker_id=worker_id,
            mapping_version_id=mapping_version_id,
        )
        if not refresh_mode:
            seed_rows = build_seed_rows(root_url=resolved_seed_url, structure_map=source.structure_map)
            allowed_seed_rows: list[dict[str, Any]] = []
            for seed_row in seed_rows:
                seed_row["mapping_version_id"] = mapping_version_id
                if urlparse(seed_row["url"]).netloc.lower() != source_domain:
                    continue
                if await robots_checker.is_allowed(seed_row["url"]):
                    allowed_seed_rows.append(seed_row)
            seed_priority, seed_page_type = score_url(resolved_seed_url, source.structure_map)
            await crud.upsert_crawl_frontier_rows(
                db,
                crawl_run_id=crawl_run.id,
                source_id=source_id,
                rows=allowed_seed_rows
                or [
                    {
                        "url": resolved_seed_url,
                        "normalized_url": normalize_url(resolved_seed_url),
                        "depth": 0,
                        "status": "queued",
                        "mapping_version_id": mapping_version_id,
                        "priority": seed_priority,
                        "predicted_page_type": seed_page_type,
                        "discovered_from_page_type": "seed",
                        "discovery_reason": "seed_root",
                    }
                ],
            )
    else:
        crawl_run = await crud.update_crawl_run(
            db,
            crawl_run.id,
            status="running",
            worker_id=worker_id,
            mapping_version_id=crawl_run.mapping_version_id or mapping_version_id,
            started_at=crawl_run.started_at or datetime.now(UTC),
            job_id=job_id or crawl_run.job_id,
        )
        mapping_version_id = crawl_run.mapping_version_id

    mapping_version = await crud.get_mapping_suggestion_draft(
        db,
        source_id=source_id,
        mapping_id=mapping_version_id,
    ) if mapping_version_id else None
    mapping_json = json.loads(mapping_version.mapping_json or "{}") if mapping_version else {}
    family_policy_by_key = {
        str(rule.get("family_key")): normalize_freshness_policy(rule.get("freshness_policy"))
        for rule in mapping_json.get("family_rules", [])
        if isinstance(rule, dict) and rule.get("family_key")
    }

    processed = 0
    changed_count = 0
    unchanged_count = 0
    await crud.recover_stale_in_progress_pages(db, source_id=source_id, stale_after_seconds=900)

    while processed < max_pages:
        source = await crud.get_source(db, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")

        if source.queue_paused or crawl_run.status == "paused":
            await crud.update_crawl_run(db, crawl_run.id, status="paused", last_heartbeat_at=datetime.now(UTC))
            await _checkpoint(
                db,
                crawl_run_id=crawl_run.id,
                source_id=source_id,
                mapping_version_id=mapping_version_id,
                status="paused",
                processed=processed,
                max_pages=max_pages,
                worker_id=worker_id,
                stage=CrawlStage.QUEUED,
            )
            await _emit_crawl_event(
                db,
                job_id=job_id,
                source_id=source_id,
                crawl_run_id=crawl_run.id,
                worker_id=worker_id,
                event_type="crawl_paused",
                message="Crawl paused by source or crawl-run control",
                stage=CrawlStage.QUEUED,
                url=None,
            )
            break
        if crawl_run.status == "cancelled":
            break

        await crud.reclaim_expired_frontier_leases(db, crawl_run_id=crawl_run.id)
        batch = await crud.claim_frontier_rows(db, crawl_run_id=crawl_run.id, worker_id=worker_id, limit=10, lease_seconds=120)

        if not batch:
            counts = await crud.get_crawl_frontier_counts(db, crawl_run.id)
            queued = counts.get("queued", 0) + counts.get("fetching", 0) + counts.get("failed_retryable", 0)
            if queued <= 0:
                await crud.update_crawl_run(
                    db,
                    crawl_run.id,
                    status="extracted",
                    completed_at=datetime.now(UTC),
                    last_heartbeat_at=datetime.now(UTC),
                    stats_json=json.dumps(counts),
                )
            await _checkpoint(
                db,
                crawl_run_id=crawl_run.id,
                source_id=source_id,
                mapping_version_id=mapping_version_id,
                status="completed" if queued <= 0 else "running",
                processed=processed,
                max_pages=max_pages,
                worker_id=worker_id,
                stage=CrawlStage.COMPLETED if queued <= 0 else CrawlStage.QUEUED,
            )
            break

        for row in batch:
            claim_lease_version = int(row.lease_version or 0)
            if processed >= max_pages:
                await crud.update_frontier_row(db, row.id, status="queued", lease_expires_at=None, leased_by_worker=None)
                continue

            if row.depth > max_depth:
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status="skipped",
                    skip_reason="max_depth_exceeded",
                    last_error="max_depth_exceeded",
                    lease_expires_at=None,
                    leased_by_worker=None,
                )
                continue

            if urlparse(row.url).netloc.lower() != source_domain:
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status="skipped",
                    skip_reason="outside_source_domain",
                    last_error="outside_source_domain",
                    lease_expires_at=None,
                    leased_by_worker=None,
                )
                continue

            # Idempotency guard: URL identity is normalized URL, not content hash.
            existing = await crud.get_page_by_normalized_url(db, source_id=source_id, normalized_url=row.normalized_url)
            if existing and existing.status in TERMINAL_PAGE_STATUSES:
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status="extracted",
                    last_extracted_at=datetime.now(UTC),
                    lease_expires_at=None,
                    leased_by_worker=None,
                )
                continue

            allowed_by_robots = await robots_checker.is_allowed(row.url)
            if not allowed_by_robots:
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status="skipped",
                    skip_reason="robots_blocked",
                    last_error="robots_blocked",
                    lease_expires_at=None,
                    leased_by_worker=None,
                )
                await _emit_crawl_event(
                    db,
                    job_id=job_id,
                    source_id=source_id,
                    crawl_run_id=crawl_run.id,
                    worker_id=worker_id,
                    event_type="crawl_policy_skipped",
                    message="URL skipped by robots policy",
                    stage=CrawlStage.FETCHING,
                    url=row.url,
                    context={"url": row.url, "reason": "robots_blocked"},
                )
                continue

            in_progress_page, _ = await crud.get_or_create_page(db, source_id=source_id, url=row.url)
            if in_progress_page.status == "completed":
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status="extracted",
                    last_extracted_at=datetime.now(UTC),
                    lease_expires_at=None,
                    leased_by_worker=None,
                )
                continue
            await crud.update_page(
                db,
                in_progress_page.id,
                status="in_progress",
                worker_id=worker_id,
                started_at=datetime.now(UTC),
                crawl_run_id=crawl_run.id,
                original_url=row.url,
                normalized_url=row.normalized_url,
            )

            await _checkpoint(
                db,
                crawl_run_id=crawl_run.id,
                source_id=source_id,
                mapping_version_id=mapping_version_id,
                status="running",
                processed=processed,
                max_pages=max_pages,
                worker_id=worker_id,
                stage=CrawlStage.FETCHING,
                last_processed_url=row.url,
            )

            while True:
                granted, retry_at = await crud.acquire_domain_rate_limit_slot(
                    db,
                    domain=source_domain,
                    min_interval_ms=1000,
                )
                if granted:
                    break
                await sleep(max(0.0, (retry_at - datetime.now(UTC)).total_seconds()))

            result = await fetch(row.url)
            now = datetime.now(UTC)

            if _is_captcha_page(result.html):
                retry_count = int(row.retry_count or 0) + 1
                retry_after_s = _parse_retry_after_seconds(None, retry_count + 2)
                retry_after_at = now + timedelta(seconds=retry_after_s)
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status="failed_retryable",
                    retry_count=retry_count,
                    retry_after=retry_after_at,
                    next_retry_at=retry_after_at,
                    last_error="captcha_detected",
                    lease_expires_at=None,
                    leased_by_worker=None,
                )
                await crud.update_crawl_run(db, crawl_run.id, status="paused", cooldown_until=retry_after_at)
                await crud.update_source(
                    db,
                    source_id,
                    queue_paused=True,
                    operational_status="paused_captcha",
                    error_message="captcha_detected",
                )
                await _emit_crawl_event(
                    db,
                    job_id=job_id,
                    source_id=source_id,
                    crawl_run_id=crawl_run.id,
                    worker_id=worker_id,
                    event_type="captcha_detected",
                    message="CAPTCHA detected, crawl paused",
                    stage=CrawlStage.FAILED,
                    url=row.url,
                    level="warning",
                    context={"url": row.url, "retry_after": retry_after_at.isoformat(), "retry_count": retry_count},
                )
                await _checkpoint(
                    db,
                    crawl_run_id=crawl_run.id,
                    source_id=source_id,
                    mapping_version_id=mapping_version_id,
                    status="paused",
                    processed=processed,
                    max_pages=max_pages,
                    worker_id=worker_id,
                    stage=CrawlStage.FAILED,
                    last_processed_url=row.url,
                )
                break

            if result.status_code in RETRYABLE_STATUS_CODES:
                retry_count = int(row.retry_count or 0) + 1
                retry_after_s = _parse_retry_after_seconds(None, retry_count)
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status="failed_retryable",
                    retry_count=retry_count,
                    retry_after=now + timedelta(seconds=retry_after_s),
                    next_retry_at=now + timedelta(seconds=retry_after_s),
                    last_status_code=result.status_code,
                    last_error=f"rate_limited_{result.status_code}",
                    lease_expires_at=None,
                    leased_by_worker=None,
                )
                await crud.update_crawl_run(db, crawl_run.id, status="cooling_down", cooldown_until=now + timedelta(seconds=retry_after_s), last_heartbeat_at=now)
                await _emit_crawl_event(
                    db,
                    job_id=job_id,
                    source_id=source_id,
                    crawl_run_id=crawl_run.id,
                    worker_id=worker_id,
                    event_type="retry_scheduled",
                    message="Rate-limited URL scheduled for retry",
                    stage=CrawlStage.FAILED,
                    url=row.url,
                    context={"url": row.url, "status_code": result.status_code, "retry_after_seconds": retry_after_s, "retry_count": retry_count},
                )
                await _checkpoint(
                    db,
                    crawl_run_id=crawl_run.id,
                    source_id=source_id,
                    mapping_version_id=mapping_version_id,
                    status="running",
                    processed=processed,
                    max_pages=max_pages,
                    worker_id=worker_id,
                    stage=CrawlStage.FAILED,
                    last_processed_url=row.url,
                )
                continue

            if result.error:
                failed_status = "failed_terminal" if int(row.retry_count or 0) >= 2 else "failed_retryable"
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status=failed_status,
                    retry_count=int(row.retry_count or 0) + 1,
                    last_error=result.error,
                    last_status_code=result.status_code,
                    lease_expires_at=None,
                    leased_by_worker=None,
                )
                await _checkpoint(
                    db,
                    crawl_run_id=crawl_run.id,
                    source_id=source_id,
                    mapping_version_id=mapping_version_id,
                    status="running",
                    processed=processed,
                    max_pages=max_pages,
                    worker_id=worker_id,
                    stage=CrawlStage.FAILED,
                    last_processed_url=row.url,
                )
                continue

            await _checkpoint(
                db,
                crawl_run_id=crawl_run.id,
                source_id=source_id,
                mapping_version_id=mapping_version_id,
                status="running",
                processed=processed,
                max_pages=max_pages,
                worker_id=worker_id,
                stage=CrawlStage.PARSING,
                last_processed_url=result.final_url,
            )

            new_content_hash = hashlib.sha256((result.html or "").encode("utf-8")).hexdigest()
            change = detect_content_change(
                previous_content_hash=row.content_hash,
                new_content_hash=new_content_hash,
                previous_etag=row.etag,
                new_etag=getattr(result, "etag", None),
                previous_last_modified=row.last_modified,
                new_last_modified=getattr(result, "last_modified", None),
            )
            family_policy = family_policy_by_key.get(row.family_key or "", "daily")
            next_eligible_fetch_at = compute_next_eligible_fetch_at(policy=family_policy, now=now)
            if refresh_mode and not force_refresh and not change.changed and row.last_fetched_at is not None:
                unchanged_count += 1
                await crud.update_frontier_row(
                    db,
                    row.id,
                    status="completed",
                    last_status_code=result.status_code,
                    last_fetched_at=now,
                    last_extracted_at=now,
                    canonical_url=result.final_url,
                    etag=getattr(result, "etag", None),
                    last_modified=getattr(result, "last_modified", None),
                    content_hash=new_content_hash,
                    next_eligible_fetch_at=next_eligible_fetch_at,
                    last_refresh_outcome="unchanged",
                    lease_expires_at=None,
                    leased_by_worker=None,
                )
                processed += 1
                continue

            await _checkpoint(
                db,
                crawl_run_id=crawl_run.id,
                source_id=source_id,
                mapping_version_id=mapping_version_id,
                status="running",
                processed=processed,
                max_pages=max_pages,
                worker_id=worker_id,
                stage=CrawlStage.EXTRACTING,
                last_processed_url=result.final_url,
            )

            page, _created = await crud.get_or_create_page(db, source_id=source_id, url=result.final_url)
            previous_page_status = page.status
            page_title = None
            parsed_html = BeautifulSoup(result.html or "", "lxml")
            if parsed_html.title and parsed_html.title.string:
                page_title = parsed_html.title.string.strip()
            update_kwargs: dict[str, Any] = {
                "crawl_run_id": crawl_run.id,
                "original_url": row.url,
                "normalized_url": normalize_url(result.final_url),
                "depth": row.depth,
                "fetch_method": result.method,
                "html": (result.html or "").replace("\x00", "")[: 500 * 1024],
                "title": page_title,
                "crawled_at": now,
                "mapping_version_id_used": mapping_version_id,
                "content_hash": new_content_hash,
                "worker_id": worker_id,
                "started_at": row.started_at or now,
            }
            completion_status = previous_page_status if (not refresh_mode and previous_page_status in TERMINAL_PAGE_STATUSES) else "fetched"
            completion_ok = await crud.complete_frontier_row_atomic(
                db,
                frontier_id=row.id,
                worker_id=worker_id,
                lease_version=claim_lease_version,
                page_id=page.id,
                page_updates={**update_kwargs, "status": completion_status},
                frontier_updates={
                    "status": "fetched",
                    "last_status_code": result.status_code,
                    "last_fetched_at": now,
                    "last_extracted_at": now,
                    "canonical_url": result.final_url,
                    "etag": getattr(result, "etag", None),
                    "last_modified": getattr(result, "last_modified", None),
                    "content_hash": new_content_hash,
                    "next_eligible_fetch_at": next_eligible_fetch_at,
                    "last_refresh_outcome": "changed" if refresh_mode else "fetched",
                    "last_change_detected_at": now if change.changed else row.last_change_detected_at,
                    "lease_expires_at": None,
                    "leased_by_worker": None,
                },
            )
            if not completion_ok:
                continue

            if change.changed:
                changed_count += 1
            elif refresh_mode:
                unchanged_count += 1

            links = _extract_links(result.html or "", result.final_url, source_domain)
            source_page_type = row.predicted_page_type or "generic"
            discovered_rows: list[dict[str, Any]] = []
            for link in links:
                # Enforce robots and domain policy before enqueue.
                if urlparse(link).netloc.lower() != source_domain:
                    continue
                if not await robots_checker.is_allowed(link):
                    continue
                priority, predicted_page_type = score_url(link, source.structure_map)
                discovered_rows.append(
                    {
                        "url": link,
                        "normalized_url": normalize_url(link),
                        "depth": row.depth + 1,
                        "status": "discovered",
                        "mapping_version_id": mapping_version_id,
                        "discovered_from_url": result.final_url,
                        "priority": priority,
                        "predicted_page_type": predicted_page_type,
                        "discovered_from_page_type": source_page_type,
                        "discovery_reason": "outlink",
                    }
                )

            if not refresh_mode and discovered_rows:
                await crud.upsert_crawl_frontier_rows(db, crawl_run_id=crawl_run.id, source_id=source_id, rows=discovered_rows)
                await crud.queue_discovered_frontier_rows(db, crawl_run_id=crawl_run.id, limit=max(100, len(discovered_rows)))

            processed += 1
            await crud.update_crawl_run(db, crawl_run.id, status="running", last_heartbeat_at=now, cooldown_until=None)
            await _checkpoint(
                db,
                crawl_run_id=crawl_run.id,
                source_id=source_id,
                mapping_version_id=mapping_version_id,
                status="running",
                processed=processed,
                max_pages=max_pages,
                worker_id=worker_id,
                stage=CrawlStage.COMPLETED,
                last_processed_url=result.final_url,
            )
            await _emit_crawl_event(
                db,
                job_id=job_id,
                source_id=source_id,
                crawl_run_id=crawl_run.id,
                worker_id=worker_id,
                event_type="page_fetched",
                message="Page fetched",
                stage=CrawlStage.COMPLETED,
                url=result.final_url,
                context={"url": result.final_url, "depth": row.depth, "stage": CrawlStage.COMPLETED},
            )

    counts = await crud.get_crawl_frontier_counts(db, crawl_run.id)
    robots_blocked = await crud.count_crawl_frontier_rows_by_error(db, crawl_run_id=crawl_run.id, last_error="robots_blocked")
    return {
        "crawl_run_id": crawl_run.id,
        "pages_crawled": counts.get("fetched", 0) + counts.get("extracted", 0),
        "changed": changed_count,
        "unchanged": unchanged_count,
        "failed": counts.get("failed_retryable", 0) + counts.get("failed_terminal", 0),
        "robots_blocked": robots_blocked,
        "queued": counts.get("queued", 0),
        "retryable": counts.get("failed_retryable", 0),
        "rate_limited": counts.get("failed_retryable", 0),
    }
