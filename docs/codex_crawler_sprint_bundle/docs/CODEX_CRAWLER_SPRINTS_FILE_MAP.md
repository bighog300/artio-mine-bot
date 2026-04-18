# Crawler Sprint File Map

This file helps Codex navigate the expected change surface for the crawler sprint work.

## Primary crawler modules

### `app/crawler/durable_frontier.py`
Main durable crawl engine.
Expected responsibilities for this work:
- robots check integration
- crawl-loop status transitions
- event/stat emission updates
- scoring hooks for discovered links
- optional post-fetch page-type refinement

### `app/crawler/link_follower.py`
Legacy crawl path.
Expected responsibilities for this work:
- source of reusable seeding/compliance logic to extract
- deprecation wrapper or transitional adapter
- eventual removal of independent queue-loop behavior

### `app/crawler/robots.py`
Robots utilities.
Expected responsibilities for this work:
- no major redesign
- used by durable frontier
- tests may need expanded coverage

### `app/crawler/automated_crawler.py`
Specialized guided crawler.
Expected responsibilities for this work:
- mostly reference-only
- useful source for follow-rule or page-typing ideas
- do not merge wholesale into durable frontier during this workstream

## DB and persistence

### `app/db/crud.py`
Expected responsibilities:
- frontier claim ordering
- frontier status updates
- frontier insert helpers
- optional metadata persistence for priority/page type

### frontier model(s)
Expected responsibilities:
- add priority metadata columns if missing

### page model(s)
Optional:
- store page type if refinement is added safely

### `alembic/versions/*`
Expected responsibilities:
- migration for frontier metadata columns
- possibly page-type field if introduced

## Orchestration and entrypoints

### `app/pipeline/runner.py`
Possible responsibilities:
- caller migration
- durable frontier invocation updates

### API / queue entrypoints
Possible responsibilities:
- route crawl requests through durable frontier
- preserve pause/resume/cancel behavior

## Tests

Likely test files to inspect first:
- `tests/test_crawler.py`
- `tests/test_crawl_state.py`
- `tests/test_crawl_rate_limit.py`
- `tests/test_pipeline.py`
- any legacy tests tied to `link_follower`

## Migration guidance

Prefer these move patterns:
- extract shared helpers first
- redirect callers second
- remove duplicate engine behavior last

Avoid these pitfalls:
- changing crawl behavior and extraction behavior in one step
- deleting legacy logic before parity is covered by tests
- introducing opaque scoring rules that are hard to validate
