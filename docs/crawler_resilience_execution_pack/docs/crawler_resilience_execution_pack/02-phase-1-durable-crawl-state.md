# Phase 1 — Durable Crawl State and Schema

## Objective

Introduce durable database-backed crawl state so that the system can persist the crawl frontier, track run lifecycle, and recover from process or worker interruption.

## Why this phase exists

Today the crawler holds too much state in memory:

- `AutomatedCrawler` tracks seen URLs in memory
- `CrawlQueue` holds queue/seen state in memory
- resume decisions are inferred from broad pipeline stage rather than exact crawl frontier state

That makes pause/resume and stale recovery fragile.

## Required deliverables

### 1. Add new persistence models

Create new SQLAlchemy models in `app/db/models.py`:

#### `CrawlRun`
Suggested fields:

- `id`
- `source_id` (FK to `Source`)
- `job_id` (nullable FK to `Job`, if you want one crawl run per job)
- `status` (`queued`, `running`, `paused`, `cooling_down`, `stale`, `completed`, `failed`, `cancelled`)
- `seed_url`
- `started_at`
- `updated_at`
- `completed_at`
- `last_heartbeat_at`
- `worker_id`
- `attempt`
- `cooldown_until`
- `stats_json`
- `error_message`

Add useful indexes for `(source_id, status)` and `last_heartbeat_at`.

#### `CrawlFrontier`
Suggested fields:

- `id`
- `crawl_run_id` (FK)
- `source_id` (FK)
- `url`
- `normalized_url`
- `depth`
- `discovered_from_url`
- `status` (`queued`, `leased`, `fetched`, `skipped`, `error`, `rate_limited`, `dead_letter`)
- `lease_expires_at`
- `leased_by_worker`
- `retry_count`
- `next_retry_at`
- `last_status_code`
- `last_error`
- `last_fetched_at`
- `content_hash` (optional)

Add a unique constraint or unique index on `(source_id, normalized_url)` so that duplicate discovery is naturally deduped.

### 2. Add migrations

Create an Alembic migration for the two new tables and indexes.

Update docs if the repo keeps migration notes in `docs/root/`.

### 3. Add CRUD helpers

Add DB helpers in `app/db/crud.py` or in a dedicated crawl-state module.

At minimum implement helpers for:

- create crawl run
- get active crawl run for source
- update crawl run heartbeat/status/stats
- insert frontier rows idempotently
- claim frontier rows in a batch
- release or complete claimed frontier rows
- mark rate-limited / retryable rows
- reclaim expired leases
- list pages/records by crawl run or source

### 4. Add URL normalization helper

Create a helper for normalized URL identity. It should:

- strip fragments
- normalize scheme/host casing
- preserve meaningful path/query where appropriate
- avoid duplicate rows for the same page because of trailing slash or fragment drift

This can live in `app/crawler/` or a small utility module.

## API changes

Add source-level or crawl-run-level read endpoints in a new route module or existing source routes:

- `GET /api/sources/{source_id}/crawl-runs`
- `GET /api/crawl-runs/{crawl_run_id}`
- `GET /api/crawl-runs/{crawl_run_id}/frontier`

Do not add mutation-heavy endpoints yet beyond what Phase 3 needs.

## Tests required

Add tests that verify:

- creating a crawl run works
- frontier deduplication works across repeated discovered URLs
- lease claim returns only eligible queued rows
- expired leases can be reclaimed
- inserting the same normalized URL twice does not create duplicates

Suggested files:

- `tests/test_crawl_state.py`
- expand `tests/test_db.py`

## Constraints

- do not remove existing `Page`/`Record` models
- do not break current crawl APIs in this phase
- maintain backward compatibility where possible
- avoid mixing enrichment state into frontier rows

## Acceptance criteria

This phase is complete when:

- durable crawl state exists in the database
- a crawl run can be created and queried
- a frontier can be populated, leased, updated, and reclaimed
- tests prove dedupe and lease recovery behavior
