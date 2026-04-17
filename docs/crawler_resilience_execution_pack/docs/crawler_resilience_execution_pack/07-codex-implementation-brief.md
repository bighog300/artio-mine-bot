# Codex Implementation Brief — Durable, Resumable Crawler

## Mission

Implement the five phases in this pack for the current Artio Miner repository.

## Scope

You are allowed to modify:

- backend models, CRUD, migrations, crawler, pipeline, API routes, and tests
- frontend live progress UI if needed for Phase 4
- docs touched by the new crawl-run system

You should avoid unrelated refactors.

## Repo-aware guidance

Use the current repo structure as the source of truth, especially:

- `app/crawler/`
- `app/pipeline/`
- `app/api/routes/`
- `app/db/models.py`
- `app/db/crud.py`
- `tests/`

There are already job progress/events and source operations. Build on them; do not replace them wholesale.

## Implementation rules

1. Prefer incremental, test-backed changes.
2. Keep crawl ingestion and enrichment separated.
3. Use durable DB-backed frontier state as the source of truth for crawl progress.
4. Make pause/resume/reclaim behavior explicit and observable.
5. Add tests as each phase lands.
6. If a migration is required, include it.
7. Preserve existing route compatibility unless a route must be extended or superseded.

## Suggested order of execution

1. schema and migration
2. CRUD helpers and URL normalization
3. lease-based worker loop
4. rate-limit persistence and stale reclaim
5. control endpoints and source/job alignment
6. SSE/progress endpoints
7. frontend live updates
8. enrichment handoff and final tests

## Definition of done

Do not consider the implementation complete unless:

- a crawl can be resumed from persisted frontier state
- retryable throttling is durable and not just in-memory delay
- stale work can be reclaimed safely
- live progress and newly crawled data are visible
- enrichment happens after crawl ingestion and can be retried independently
- tests cover the lifecycle
