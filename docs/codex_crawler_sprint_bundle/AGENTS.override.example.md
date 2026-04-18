# AGENTS.override.md — Crawler Sprint Execution Override

This override applies only to the crawler consolidation workstream.

## Scope lock

Only work on the crawler milestones documented in:
- `docs/CODEX_CRAWLER_SPRINTS_OVERVIEW.md`
- `docs/CODEX_CRAWLER_SPRINT_1_ROBOTS_COMPLIANCE.md`
- `docs/CODEX_CRAWLER_SPRINT_2_SINGLE_CRAWL_ENGINE.md`
- `docs/CODEX_CRAWLER_SPRINT_3_PRIORITY_AWARE_DURABLE_CRAWL.md`
- `docs/CODEX_CRAWLER_SPRINTS_CHECKLIST.md`
- `docs/CODEX_CRAWLER_SPRINTS_FILE_MAP.md`

Do not widen scope beyond those documents.

## Repository assumptions

- Durable crawl lives in `app/crawler/durable_frontier.py`.
- Legacy crawl logic lives in `app/crawler/link_follower.py`.
- Robots logic lives in `app/crawler/robots.py`.
- Frontier and page persistence are handled through DB models and `app/db/crud.py`.
- The pipeline orchestrator and API routes may need small caller updates, but extraction remains a downstream concern.

## Working rules

- Make the smallest change that satisfies the sprint acceptance criteria.
- Preserve current route shapes and operator flows unless the sprint docs explicitly require a change.
- Do not redesign the crawler from scratch.
- Prefer helper extraction over parallel implementations.
- Keep durable frontier as the single production crawl engine.
- Keep extraction and crawl policy separate.
- Add or update tests for each changed behavior.
- Summarize changed files, migrations, test coverage, and any follow-up work after each sprint.

## Sprint order

1. Robots compliance
2. Single crawl engine
3. Priority-aware durable crawl

Do not start a later sprint until the current sprint passes its own verification checklist.
