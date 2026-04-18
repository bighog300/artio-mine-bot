# Sprint 1: Robots Compliance in Durable Frontier

## Summary

Add `robots.txt` enforcement to `run_durable_crawl()` so the production crawler path becomes policy-compliant before fetching URLs.

## Goal

Every URL claimed by the durable frontier must be checked against robots rules before fetch. Disallowed URLs must be marked as skipped and must not be retried.

## Primary files

- `app/crawler/durable_frontier.py`
- `app/crawler/robots.py`
- `app/db/crud.py`
- tests covering durable crawl and robots behavior

## Required changes

### 1. Integrate `RobotsChecker`
- Instantiate or inject `RobotsChecker` inside `run_durable_crawl()`.
- Use a single checker instance for the crawl loop to benefit from per-domain caching.

### 2. Check robots before fetch
- Before `fetch(url)`, call `await robots_checker.is_allowed(url)`.
- If disallowed:
  - mark the frontier row as `skipped`
  - set a machine-readable reason such as `robots_blocked`
  - clear or close the lease correctly
  - emit a crawl event or progress marker

### 3. Preserve policy semantics
- Do not count robots blocks as fetch errors.
- Do not retry disallowed URLs.
- Prefer not to create a `pages` row for robots-blocked URLs in this sprint.

### 4. Surface the result
- Add a robots-blocked counter to crawl-run stats or event summaries where practical.
- Ensure logs and progress reporting clearly distinguish:
  - fetched
  - errored
  - skipped by policy

## Acceptance criteria

- Durable crawl does not fetch a robots-disallowed URL.
- Disallowed URLs are marked as skipped, not errored.
- Robots-blocked URLs are not retried.
- Crawl reporting surfaces robots-blocked counts or events.
- Relevant tests are added or updated.

## Constraints

- Do not redesign `RobotsChecker`.
- Do not move robots logic into a separate service.
- Do not bundle unrelated crawler refactors into this sprint.

## Suggested verification

Run targeted tests first. If local deps are available, prefer:
```bash
pytest -q tests/test_crawler.py tests/test_crawl_rate_limit.py tests/test_crawl_state.py
```

Also run:
```bash
python -m compileall app
```

If robot-specific tests live elsewhere, include them in the run.

## Expected output from Codex

Provide:
- files changed
- behavior changes
- whether a migration was needed
- tests added or updated
- any follow-up caveats
