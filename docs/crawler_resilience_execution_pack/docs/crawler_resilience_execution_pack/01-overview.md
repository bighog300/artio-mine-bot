# Crawler Resilience & Real-Time Execution Pack

## Goal

Upgrade the current crawler so that it can:

1. persist crawl state durably
2. pause, resume, cancel, and recover from stale or rate-limited crawls
3. stream progress and newly crawled data in near real time
4. keep enrichment separate so enrichment runs after crawl data has been stored

This pack is written for the current Artio Miner repository and is intended to be executed by Codex in phases.

## Current repo baseline

The repo already has useful building blocks:

- crawler logic in `app/crawler/automated_crawler.py`, `app/crawler/link_follower.py`, and `app/crawler/fetcher.py`
- job orchestration in `app/pipeline/runner.py`
- job progress and events in `app/pipeline/job_progress.py`
- persistence models in `app/db/models.py`
- source and operational controls in `app/api/routes/sources.py`, `app/api/routes/operations.py`, and `app/api/routes/mine.py`
- a clean conceptual split between crawling and enrichment in `app/api/routes/sources.py` and `app/pipeline/runner.py`

The main weakness is that crawl state is still mostly in memory. Job rows exist, but the frontier of URLs to visit, retry, or reclaim after worker failure is not durably persisted.

## Design outcome

After these phases, the crawler should behave like this:

- a crawl starts by creating a `crawl_run`
- discovered URLs are written into a durable `crawl_frontier`
- workers lease frontier rows in batches
- rate-limited URLs move into retry/cooldown state instead of being lost
- stale workers can be detected and their leases reclaimed
- source pause/resume affects active crawling in a predictable way
- the UI can display live crawl events, counters, and newly fetched pages/records
- enrichment runs after crawl ingestion and can be retried independently

## Non-goals

These phases should not attempt to:

- redesign the entire extraction or AI classification stack
- rebuild the frontend from scratch
- replace the existing jobs/events system
- implement distributed scheduling across many queues in one phase

## Execution order

1. Phase 1 — Durable crawl state and schema
2. Phase 2 — Lease-based crawl engine and resume semantics
3. Phase 3 — Rate-limit resilience, stale recovery, and operator controls
4. Phase 4 — Real-time progress and newly crawled data visibility
5. Phase 5 — Enrichment decoupling, backfills, tests, and rollout hardening

## Acceptance bar for the whole pack

The full implementation is complete only when:

- an interrupted crawl can resume without re-walking the full site
- a 429 or temporary source throttle causes retry/cooldown, not manual restart
- stale jobs can be reclaimed safely
- pages and records appear during the crawl in the API/UI
- enrichment can be triggered after crawl completion without blocking crawl ingestion
- targeted tests cover pause, resume, stale recovery, rate limiting, and live progress output
