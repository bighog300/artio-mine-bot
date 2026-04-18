# Sprint 3: Priority-Aware Durable Crawl

## Summary

Teach durable frontier to prioritize likely high-value URLs without turning the crawler into a full extractor.

## Goal

Frontier rows should be able to carry priority and predicted page-type hints so the crawler claims better pages earlier than uniform BFS would.

## Primary files

- `app/crawler/durable_frontier.py`
- `app/crawler/crawl_policy.py` (new)
- `app/db/crud.py`
- frontier model and Alembic migration
- page model updates if page type is stored
- crawl-order tests

## Required changes

### 1. Add frontier metadata
Add fields such as:
- `priority`
- `predicted_page_type`
- `discovered_from_page_type`
- `discovery_reason`

Use an Alembic migration if the frontier table requires new columns.

### 2. Claim higher-priority work first
Update frontier claim ordering to prefer:
1. highest priority
2. lowest depth
3. oldest discovery time

Preserve lease safety and concurrent claiming behavior.

### 3. Add a lightweight crawl-policy layer
Create `app/crawler/crawl_policy.py` with small, explainable helpers such as:
- `predict_page_type(url, source, structure_map)`
- `score_url(url, source, structure_map)`

The scoring system should use:
- structure-map hints when present
- simple URL heuristics when not present
- conservative deprioritization for utility/legal pages
- bounded numeric priorities

### 4. Score discovered links before enqueue
- Apply URL scoring to outlinks during durable crawl.
- Persist priority metadata on frontier insert.
- Continue enforcing max depth and URL dedupe.

### 5. Optional post-fetch refinement
If the page model already supports it or can be extended safely:
- refine page type after fetch using title/HTML signals
- persist `page_type`
- use the refined current-page type to score child links better

Keep this lightweight. Do not do full record extraction in this sprint.

## Acceptance criteria

- Frontier rows can carry priority and page-type hints.
- Claim ordering uses priority ahead of plain queue order.
- Discovered links are no longer enqueued uniformly.
- Mapped sites benefit from structure hints.
- Unmapped sites still crawl correctly with generic heuristics.
- Tests validate crawl-order behavior.

## Constraints

- Do not move extraction into durable crawl.
- Do not create a second policy engine in parallel with durable frontier.
- Keep heuristics simple and explainable.
- Avoid starvation of low-priority pages where practical.

## Suggested verification

```bash
pytest -q tests/test_crawler.py tests/test_pipeline.py
python -m compileall app
```

If a dedicated durable frontier test file exists by this point, include it.

## Expected output from Codex

Provide:
- files changed
- migration added
- fields added
- scoring behavior introduced
- tests demonstrating improved crawl order
- any known limitations, including starvation risk or heuristic gaps
