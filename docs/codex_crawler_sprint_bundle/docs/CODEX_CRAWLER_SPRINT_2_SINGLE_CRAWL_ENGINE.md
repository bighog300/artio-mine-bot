# Sprint 2: Single Crawl Engine

## Summary

Make durable frontier the single production crawl engine by extracting shared seeding logic, routing legacy callers through durable crawl, and deprecating `link_follower` as a standalone engine.

## Goal

There should no longer be two competing general crawl engines with separate behavior contracts.

## Primary files

- `app/crawler/durable_frontier.py`
- `app/crawler/link_follower.py`
- `app/crawler/seeding.py` (new)
- `app/pipeline/runner.py`
- crawl-related API or queue entrypoints
- crawl tests

## Required changes

### 1. Establish the canonical engine
- Treat `run_durable_crawl()` as the production crawler.
- Mark `link_follower.crawl_source()` as deprecated or reduce it to a compatibility wrapper.

### 2. Extract shared seeding
- Create `app/crawler/seeding.py`.
- Move reusable logic for:
  - root URL seeding
  - structure-map-derived target seeding
  - normalization and dedupe
  - initial depth assignment
- Reuse this helper from durable frontier initialization.

### 3. Route callers to durable frontier
- Find all code paths that still invoke `crawl_source()` directly.
- Route them through durable frontier or a temporary wrapper that delegates into durable frontier.
- Preserve pause/resume/cancel behavior.

### 4. Migrate test coverage
- Update tests that encode `link_follower`-specific queue semantics.
- Keep behavior-based tests for:
  - root seeding
  - structure-target seeding
  - frontier progression
  - terminal state handling

### 5. Retire the independent engine
- Remove duplicate queue-loop behavior from `link_follower` once callers and tests no longer depend on it.
- Keep only intentionally shared helpers, or delete the module in a later pass if safer.

## Acceptance criteria

- No production crawl entrypoint relies on `link_follower` as an independent engine.
- Shared seeding logic lives outside `link_follower`.
- Durable frontier owns crawl-run and frontier-state progression.
- Tests no longer require dual-engine behavior contracts.
- `link_follower` is clearly deprecated, wrapped, or removed.

## Constraints

- Do not change extraction ownership in this sprint.
- Do not merge `automated_crawler` into durable frontier.
- Do not widen scope into unrelated API redesign.

## Suggested verification

```bash
pytest -q tests/test_crawler.py tests/test_pipeline.py tests/test_crawl_state.py
python -m compileall app
```

If there are targeted tests for live progress or job orchestration, include them.

## Expected output from Codex

Provide:
- files changed
- new helper modules added
- callers migrated
- tests migrated or deleted
- whether `link_follower` remains as a wrapper or was fully removed
