# Codex Brief: Crawler Sprint Overview

## Objective

Consolidate the crawler into a compliant, priority-aware durable frontier.

The intended end state is:

- `run_durable_crawl()` is the single production crawl engine.
- Durable crawl enforces `robots.txt` before fetch.
- `link_follower` is deprecated and then removed as an independent engine.
- Durable crawl can prioritize frontier rows by likely page value.
- The crawler remains fetch- and frontier-focused. Extraction remains downstream.

## Why this work exists

The current crawler implementation is split across:
- `app/crawler/durable_frontier.py`
- `app/crawler/link_follower.py`
- `app/crawler/automated_crawler.py`

The durable frontier has the stronger operational model, but it is missing robots enforcement and crawl-policy awareness. The legacy path still contains useful seeding and compliance behavior, which should be extracted rather than maintained as a second engine.

## Sprint sequence

### Sprint 1 — Robots compliance
Add robots enforcement to durable crawl and surface the result in stats and tests.

### Sprint 2 — Single crawl engine
Extract shared seeding logic, route legacy callers through durable frontier, migrate tests, and retire `link_follower` as a standalone engine.

### Sprint 3 — Priority-aware durable crawl
Add frontier priority metadata, priority-aware claim ordering, and a lightweight crawl-policy layer for smarter enqueue behavior.

## Scope boundaries

In scope:
- Durable frontier
- Shared seeding
- Robots enforcement
- Frontier metadata and claim ordering
- Crawl policy heuristics
- Caller migration
- Test migration
- Small DB migrations needed for frontier metadata

Out of scope:
- Rewriting extraction as part of crawl
- Replacing `automated_crawler` in this sprint sequence
- UI redesign
- Unrelated auth, settings, or deployment refactors
- Re-architecting queue infrastructure

## Key principles

1. Durable frontier is canonical.
2. Policy skips are not fetch failures.
3. Smart crawl ordering must remain explainable.
4. Low-priority exploration must still be possible.
5. Extraction should remain downstream.

## Definition of done

This work is complete when:
- no production crawl path depends on `link_follower` queue semantics
- durable crawl never fetches a robots-disallowed URL
- frontier rows can carry priority and predicted page-type hints
- higher-value URLs are claimed before utility pages under the same crawl budget
- tests cover robots behavior, caller migration parity, and crawl ordering
