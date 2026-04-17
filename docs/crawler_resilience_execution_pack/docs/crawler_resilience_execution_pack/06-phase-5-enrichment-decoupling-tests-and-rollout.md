# Phase 5 — Enrichment Decoupling, Tests, and Rollout Hardening

## Objective

Make crawl ingestion and enrichment cleanly separable so crawled data appears immediately, while enrichment runs later and can be retried independently.

## Current repo touchpoints

Primary files likely involved:

- `app/pipeline/runner.py`
- `app/api/routes/sources.py`
- `app/db/models.py`
- `app/db/crud.py`
- existing enrichment and extraction modules under `app/extraction/` and `app/ai/`

## Required deliverables

### 1. Formalize the stage split

The system should clearly support:

- Crawl stage: fetch/store/classify pages, create minimally useful records
- Enrichment stage: run heavier extraction, AI enrichment, linking, media, completeness, backfill, or provenance work after crawl ingestion

Already fetched data must be visible before enrichment completes.

### 2. Add explicit post-crawl handoff behavior

Support one or both of these modes:

- manual: user starts enrichment after crawl completes
- automatic: crawl completion enqueues enrichment if enabled by config or source settings

Whichever mode is chosen, keep the boundary explicit and traceable in job events.

### 3. Improve idempotency for enrichment

Enrichment retries should:

- operate on fetched pages/records that are safe to reprocess
- avoid duplicate record creation
- update existing records when intended
- keep provenance or source references intact

### 4. Rollout and fallback documentation

Document how to deploy the new crawl-run system gradually.

Suggested rollout steps:

1. migrate schema
2. enable durable crawl state behind a feature flag if needed
3. verify new crawl-run APIs in staging
4. enable SSE UI updates
5. switch resume behavior to crawl-run aware mode
6. monitor stale reclaim and retry metrics

### 5. Test matrix

Add or update tests for:

- crawl only, no enrichment
- crawl then enrichment
- pause during crawl, resume, then enrich
- rate-limited crawl that later resumes and completes
- stale worker recovery followed by completion
- newly crawled pages visible before enrichment completes

Suggested files:

- `tests/test_crawl_resume.py`
- `tests/test_crawl_rate_limit.py`
- `tests/test_api.py`
- `tests/test_pipeline.py`
- `tests/test_operations_sprints.py`

## Constraints

- do not tightly couple enrichment completion to crawl success responses
- keep backward compatibility where existing source enrichment endpoints already exist

## Acceptance criteria

This phase is complete when:

- crawled pages/records are visible before enrichment completes
- enrichment is a separate, retryable concern
- tests cover the end-to-end lifecycle from crawl to enrichment
- docs explain safe rollout and operator expectations
