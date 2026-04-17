# Phase 4 — Real-Time Progress and Newly Crawled Data Visibility

## Objective

Expose live crawl progress, live crawl events, and newly crawled pages/records while the crawl is still running.

## Current repo touchpoints

Primary files likely involved:

- `app/pipeline/job_progress.py`
- `app/api/routes/operations.py`
- `app/api/routes/sources.py`
- `app/api/main.py`
- frontend files under `frontend/src/`

## Required deliverables

### 1. Introduce live crawl progress payloads

Add a read model for crawl progress that includes honest counters instead of weak percentage-only estimates.

Suggested fields:

- `crawl_run_id`
- `status`
- `queued_count`
- `leased_count`
- `fetched_count`
- `skipped_count`
- `error_count`
- `rate_limited_count`
- `records_created`
- `records_updated`
- `pages_visible`
- `last_event_at`
- `cooldown_until`

If a percent is shown, compute it from frontier completion status, not `source.total_pages` alone.

### 2. Add server-sent events for live updates

Add SSE endpoints such as:

- `GET /api/jobs/{job_id}/stream`
- `GET /api/crawl-runs/{crawl_run_id}/stream`
- optionally `GET /api/sources/{source_id}/stream`

Each event should be compact JSON and cover:

- heartbeat
- page fetched
- page skipped
- retry scheduled
- record created
- record updated
- crawl paused/resumed/completed
- stale reclaimed

SSE is preferred over WebSockets for this phase because it is simpler and fits the existing event model.

### 3. Surface newly crawled data immediately

Expose list/read APIs so the frontend can fetch pages and records discovered during the current crawl.

Useful endpoints:

- `GET /api/crawl-runs/{crawl_run_id}/pages`
- `GET /api/crawl-runs/{crawl_run_id}/records`

If schema changes are minimal, source-scoped filtering is acceptable as long as it can isolate the current crawl.

### 4. Frontend live updates

Update the frontend to:

- subscribe to the SSE stream while a crawl is active
- update counters live
- append pages/records as they appear
- show cooldown state clearly
- show paused/running/stale/completed state clearly

Do not block rendering on enrichment.

## Tests required

Add tests that verify:

- progress payload returns correct crawl-run counters
- SSE endpoint emits expected event types
- pages and records lists show items created during the crawl

If end-to-end SSE testing is heavy, at least add backend route tests and unit tests around event serialization.

## Constraints

- keep polling fallbacks for environments where SSE may be unavailable
- do not require full frontend redesign
- avoid chatty per-token style event streams; event at useful workflow milestones

## Acceptance criteria

This phase is complete when:

- operators can see live crawl progress and cooldown state
- newly crawled pages/records appear during the crawl
- the UI reflects pause/resume/stale/completed transitions in real time
