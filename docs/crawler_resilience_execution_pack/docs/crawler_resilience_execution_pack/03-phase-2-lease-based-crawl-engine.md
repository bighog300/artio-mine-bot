# Phase 2 — Lease-Based Crawl Engine and Resume Semantics

## Objective

Refactor crawl execution so that workers process a durable frontier from the database instead of relying on recursive or in-memory queue state.

## Current repo touchpoints

Primary files likely involved:

- `app/crawler/automated_crawler.py`
- `app/crawler/link_follower.py`
- `app/crawler/fetcher.py`
- `app/pipeline/runner.py`
- `app/api/routes/mine.py`
- `app/api/routes/sources.py`

## Required deliverables

### 1. Replace in-memory frontier ownership with DB-backed leasing

Refactor crawling so the worker loop does the following:

1. create or load an active `CrawlRun`
2. seed initial frontier rows
3. claim a batch of `queued` eligible frontier rows
4. fetch/process each leased row
5. discover links and insert them into `CrawlFrontier`
6. mark the current row `fetched`, `skipped`, `error`, or `rate_limited`
7. repeat until no eligible rows remain

The system should no longer rely on in-memory queue state as the source of truth.

### 2. Define true resume semantics

Update resume behavior so that resuming a crawl means:

- reusing the existing active or paused `CrawlRun` for the source where appropriate
- continuing queued, leased-expired, or retry-eligible frontier rows
- not starting from scratch unless explicitly requested

Review current logic around `_choose_resume_job_type()` in `app/api/routes/mine.py` and replace stage inference with crawl-run state where needed.

### 3. Seed handling

The crawl seed logic should insert initial frontier rows deterministically from the source root, sitemap, or mapping configuration.

Where the current crawler supports path rules, keep them. Discovery must filter through existing scope rules before frontier insertion.

### 4. Job and crawl-run coupling

Integrate `Job` and `CrawlRun` cleanly:

- a crawl job should reference its active crawl run
- job progress should derive from crawl-run counters when possible
- heartbeats should update both job and crawl run

## Tests required

Add tests that verify:

- a crawl run can resume after a simulated interruption without losing discovered frontier rows
- duplicate links discovered twice are not re-enqueued
- the worker claims batches correctly and completes the crawl when frontier is drained
- a stopped crawl can be resumed from the exact frontier state

Suggested files:

- `tests/test_crawl_resume.py`
- extend `tests/test_crawler.py`
- extend `tests/test_pipeline.py`

## Constraints

- do not break existing page persistence and extraction behavior
- keep enrichment work out of the crawl worker path in this phase
- preserve existing crawl classification and fetch logic unless needed for the durable frontier

## Acceptance criteria

This phase is complete when:

- active crawl execution uses DB frontier leasing as the source of truth
- resume continues outstanding crawl work instead of broad stage guesses
- interrupted crawls continue from persisted state
