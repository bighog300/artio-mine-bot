# Phase 3 — Rate-Limit Resilience, Stale Recovery, and Operator Controls

## Objective

Make crawling robust against 429s, temporary blocks, stale workers, and operator pause/resume/cancel actions.

## Current repo touchpoints

Primary files likely involved:

- `app/crawler/fetcher.py`
- `app/pipeline/runner.py`
- `app/api/routes/operations.py`
- `app/api/routes/sources.py`
- `app/db/models.py`
- `app/db/crud.py`

## Required deliverables

### 1. Turn rate limiting into first-class persisted state

When a fetch encounters retryable throttling, especially `429` or `503`, the system should:

- detect the status code
- parse `Retry-After` if present
- set `next_retry_at` on the frontier row
- move the row to `rate_limited` or equivalent retryable state
- optionally set `crawl_run.cooldown_until` when the whole source/domain is cooling down
- emit an event describing the cooldown

### 2. Add lease expiry and stale reclamation

Extend stale handling so that if a worker heartbeat expires:

- the crawl run is marked `stale`
- frontier rows leased by the dead worker with expired leases are moved back to `queued`
- the system can resume without operator data repair

Review current stale detection around `_is_job_stale()` and make it actionable.

### 3. Align source pause/resume with active crawl execution

Currently source pause flags and job pause logic are not fully aligned.

Update controls so that:

- pausing a source pauses active crawl execution for that source
- resuming a source re-enables eligible frontier processing
- cancelling a source or crawl run stops new leases and releases or expires in-flight work safely

The worker checkpoint logic should observe both job-level and source-level control signals.

### 4. Add explicit crawl-run control endpoints

Add API endpoints such as:

- `POST /api/crawl-runs/{crawl_run_id}/pause`
- `POST /api/crawl-runs/{crawl_run_id}/resume`
- `POST /api/crawl-runs/{crawl_run_id}/cancel`
- `POST /api/crawl-runs/{crawl_run_id}/reclaim-stale`

Keep source-level controls too, but make crawl-run control explicit.

## Tests required

Add tests that verify:

- a 429 marks work retryable instead of failed permanently
- `Retry-After` delays retry eligibility
- a stale worker lease can be reclaimed and resumed
- pausing a source halts further crawl progress
- resuming a source resumes work without duplicating already-completed pages

Suggested files:

- `tests/test_crawl_rate_limit.py`
- `tests/test_operations_sprints.py`
- `tests/test_pipeline.py`

## Constraints

- avoid broad hidden retries that mask failure forever
- keep max retry count bounded
- preserve error observability so operators know why the crawl is cooling down

## Acceptance criteria

This phase is complete when:

- retryable throttling becomes durable cooldown state
- stale leases can be reclaimed and resumed safely
- operator controls affect actual crawl behavior, not only metadata
