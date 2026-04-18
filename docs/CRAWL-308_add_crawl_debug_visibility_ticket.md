# CRAWL-308 — Add crawl debug visibility for frontier priority and skip reasons

## Summary

Add debug and admin visibility for crawl frontier priority metadata and skip reasons so operators can inspect why URLs are being claimed, delayed, or skipped.

## Why

The durable frontier now supports:
- priority-aware claiming
- predicted page-type hints
- policy skips such as `robots_blocked`

These changes improve crawl behavior, but they also make the crawler harder to reason about without observability. Operators need a way to inspect frontier decisions and verify that:
- high-value URLs are actually being prioritized
- skipped URLs are skipped for the expected reasons
- low-priority URLs are delayed rather than silently lost
- policy behavior is working as intended in production

This ticket adds the visibility layer needed to validate and tune the new crawler behavior safely.

## Scope

**In scope**
- Expose frontier metadata in crawl debug/admin surfaces
- Show per-row fields such as:
  - `priority`
  - `predicted_page_type`
  - `discovered_from_page_type`
  - `discovery_reason`
  - `status`
  - skip reason or `last_error` where currently used
- Add filtering or query support for:
  - skipped rows
  - `robots_blocked`
  - high-priority rows
  - low-priority rows
  - page type or predicted page type
- Make it possible to inspect claim-order decisions for a crawl run or source
- Add targeted tests for any new API/query behavior

**Out of scope**
- Redesigning the crawler UI
- Reworking frontier storage schema beyond small additions needed for debug visibility
- Changing crawl policy heuristics as part of this ticket
- Building a full analytics/dashboard system

## Dependencies

- CRAWL-101 — durable robots compliance
- CRAWL-301 — frontier priority metadata
- CRAWL-302 — priority-aware claiming
- CRAWL-304 — scoring links before enqueue

## Files likely to change

- `app/api/routes/...` crawl/debug/admin endpoints
- `app/db/crud.py`
- `app/crawler/durable_frontier.py` (only if debug/event payloads need small additions)
- frontend admin/debug page(s), if present
- tests for crawl API/debug visibility

## Proposed implementation

### 1. Expose frontier decision fields
Update the relevant debug/admin API route(s) to return frontier metadata including:
- normalized URL
- depth
- status
- priority
- predicted page type
- discovered-from page type
- discovery reason
- skip reason / `last_error`
- timestamps relevant to claimability if already available

### 2. Add query/filter support
Support useful inspection filters such as:
- `status=skipped`
- `skip_reason=robots_blocked`
- `min_priority=...`
- `max_priority=...`
- `predicted_page_type=...`

Keep the implementation simple and operator-focused.

### 3. Show claim-order explainability
Where practical, make it easy to confirm why a row is likely to be claimed before another one by exposing the fields used in claim ordering:
- priority
- depth
- created_at / discovery time

### 4. Add tests
Add coverage showing:
- frontier rows expose priority metadata
- robots-blocked rows can be filtered or identified clearly
- returned ordering reflects the claim-order fields where applicable

## Acceptance criteria

- [ ] Operators can inspect frontier rows with priority and skip metadata
- [ ] `robots_blocked` rows are clearly distinguishable from fetch failures
- [ ] There is at least one supported way to filter or query skipped frontier rows by reason
- [ ] There is at least one supported way to inspect high- vs low-priority rows
- [ ] Tests cover the new visibility behavior

## Verification

```bash
python -m compileall app
pytest -q
```

At minimum, run targeted tests for:
- crawl debug/admin routes
- frontier query/filter behavior
- any frontend or API serialization touched by this change

## Risks / rollout notes

- If skip reasons are currently stored in `last_error`, keep the API wording clear so operators do not confuse policy skips with fetch failures.
- Avoid exposing overly noisy internal fields unless they materially help debugging.
- If there is no existing admin surface, start with API/debug endpoint visibility before adding UI work.

## Codex handoff output

Please include:
- summary of changes
- files changed
- API/debug surfaces updated
- tests added or updated
- any follow-up recommendation, especially if `last_error` should later be split into a dedicated `skip_reason`
