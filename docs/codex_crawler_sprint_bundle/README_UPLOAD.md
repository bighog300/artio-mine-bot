# Codex Crawler Sprint Bundle

This bundle is designed to be uploaded at the **repository root**.

## Included files

- `docs/CODEX_CRAWLER_SPRINTS_OVERVIEW.md`
- `docs/CODEX_CRAWLER_SPRINT_1_ROBOTS_COMPLIANCE.md`
- `docs/CODEX_CRAWLER_SPRINT_2_SINGLE_CRAWL_ENGINE.md`
- `docs/CODEX_CRAWLER_SPRINT_3_PRIORITY_AWARE_DURABLE_CRAWL.md`
- `docs/CODEX_CRAWLER_SPRINTS_CHECKLIST.md`
- `docs/CODEX_CRAWLER_SPRINTS_EXECUTION_PROMPT.txt`
- `docs/CODEX_CRAWLER_SPRINTS_FILE_MAP.md`
- `.github/ISSUE_TEMPLATE/crawler-sprint-ticket.md`
- `AGENTS.override.example.md`

## Recommended use

1. Upload these files into the repo root, preserving paths.
2. Keep your existing `AGENTS.md` unchanged.
3. For a focused Codex run on this workstream, optionally copy:
   - `AGENTS.override.example.md` -> `AGENTS.override.md`
4. Paste `docs/CODEX_CRAWLER_SPRINTS_EXECUTION_PROMPT.txt` into Codex when starting the work.
5. Execute one sprint at a time in this order:
   - Sprint 1: Robots compliance
   - Sprint 2: Single crawl engine
   - Sprint 3: Priority-aware durable crawl

## Notes

- The sprint docs are written to match the current repository layout and the crawler review already completed.
- The docs assume the durable frontier is the production crawler path and that extraction should remain downstream.
- The issue template is generic so you can create one GitHub issue per ticket.
