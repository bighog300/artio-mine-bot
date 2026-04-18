# Crawler Sprint Checklist and Ticket Board

## Milestone 1 — Robots compliance

### CRAWL-101 — Add robots checks to durable frontier
- [ ] integrate `RobotsChecker` into `run_durable_crawl()`
- [ ] skip disallowed URLs before fetch
- [ ] mark frontier row as skipped with `robots_blocked`
- [ ] ensure blocked URLs are not retried
- [ ] emit crawl events or stats for blocked URLs

Depends on: none

### CRAWL-102 — Add robots-aware crawl stats and events
- [ ] track `robots_blocked_count`
- [ ] expose the count or event in reporting surfaces

Depends on: CRAWL-101

### CRAWL-103 — Add tests for durable robots enforcement
- [ ] allowed URL proceeds to fetch
- [ ] blocked URL is skipped
- [ ] blocked URL is not retried
- [ ] robots caching behavior is covered

Depends on: CRAWL-101

---

## Milestone 2 — Single crawl engine

### CRAWL-201 — Declare durable frontier canonical
- [ ] mark durable frontier as the production crawler
- [ ] mark `link_follower` deprecated
- [ ] update crawler docs where needed

Depends on: CRAWL-101 preferred

### CRAWL-202 — Extract shared seeding module
- [ ] create `app/crawler/seeding.py`
- [ ] move root seeding logic
- [ ] move structure-target seeding logic
- [ ] normalize and dedupe seeds

Depends on: CRAWL-201

### CRAWL-203 — Route callers through durable frontier
- [ ] identify all `crawl_source()` callers
- [ ] replace direct calls or wrap them through durable frontier
- [ ] preserve pause/resume/cancel behavior

Depends on: CRAWL-202

### CRAWL-204 — Migrate tests to durable frontier semantics
- [ ] rewrite legacy crawl tests as behavior-based durable tests
- [ ] keep parity tests for seeding and terminal state behavior

Depends on: CRAWL-202, CRAWL-203

### CRAWL-205 — Remove or freeze `link_follower`
- [ ] remove independent queue-loop behavior
- [ ] clean imports
- [ ] delete dead tests

Depends on: CRAWL-203, CRAWL-204

---

## Milestone 3 — Priority-aware durable crawl

### CRAWL-301 — Add frontier priority metadata
- [ ] add `priority`
- [ ] add `predicted_page_type`
- [ ] add `discovered_from_page_type`
- [ ] add `discovery_reason`
- [ ] add Alembic migration

Depends on: CRAWL-203 preferred

### CRAWL-302 — Make frontier claiming priority-aware
- [ ] order by priority, then depth, then age
- [ ] verify claim safety under concurrent leases

Depends on: CRAWL-301

### CRAWL-303 — Add lightweight crawl-policy module
- [ ] create `app/crawler/crawl_policy.py`
- [ ] implement `predict_page_type`
- [ ] implement `score_url`
- [ ] support generic heuristics and structure-map hints

Depends on: CRAWL-301

### CRAWL-304 — Score links before enqueue
- [ ] score each discovered link
- [ ] persist priority metadata on frontier insert
- [ ] keep dedupe and max-depth behavior intact

Depends on: CRAWL-302, CRAWL-303

### CRAWL-305 — Refine page type after fetch
- [ ] optionally infer page type from fetched HTML/title
- [ ] store page type if supported
- [ ] use refined type to improve child-link scoring

Depends on: CRAWL-303, CRAWL-304

### CRAWL-306 — Support follow-policy hints from structure maps
- [ ] read follow hints from runtime map when available
- [ ] boost or de-prioritize links accordingly

Depends on: CRAWL-303, CRAWL-304

### CRAWL-307 — Add crawl-order validation tests
- [ ] validate detail pages are claimed before utility pages
- [ ] validate unmapped sites still crawl
- [ ] validate low-priority pages are still reachable

Depends on: CRAWL-302, CRAWL-304

---

## Recommended implementation order

1. CRAWL-101
2. CRAWL-102
3. CRAWL-103
4. CRAWL-201
5. CRAWL-202
6. CRAWL-203
7. CRAWL-204
8. CRAWL-301
9. CRAWL-302
10. CRAWL-303
11. CRAWL-304
12. CRAWL-305
13. CRAWL-306
14. CRAWL-307
15. CRAWL-205

## Sprint completion criteria

A sprint is ready to merge when:
- scoped acceptance criteria are satisfied
- targeted tests pass
- compile/import checks pass
- changed files and follow-up caveats are documented in the Codex handoff
