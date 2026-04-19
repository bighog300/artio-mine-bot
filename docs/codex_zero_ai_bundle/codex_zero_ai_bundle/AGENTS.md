# AGENTS.md — Zero-AI Runtime Mining Retrofit

## Mission

Implement a new operating model for this repository:

1. When a source is created, run a one-time **discovery flow**.
2. Discovery may use AI to inspect the site structure, propose mining targets, and generate a durable runtime mapping.
3. After a runtime mapping is published for a source, all normal crawl/mining jobs must run with **zero AI token usage**.
4. If deterministic runtime extraction cannot classify or extract a page, the page must be queued for review or remapping. Runtime must **not** fall back to AI.

## Non-negotiable outcome

Normal runtime crawl, enrichment, and reprocessing for a published source must not call OpenAI at all.

## Existing architecture notes

The repo already contains:

- AI-assisted site structure analysis and discovery helpers
- a deterministic crawler path in `app/crawler/automated_crawler.py`
- an AI-heavy extraction path in `app/pipeline/runner.py`

The implementation goal is to make the deterministic runtime path the default for published sources and confine AI usage to discovery/remapping workflows.

## Hard constraints

- Do not introduce any runtime AI fallback for published sources.
- Do not keep the old “AI extraction by default” behavior in the normal mining path.
- Prefer additive, backwards-compatible changes where feasible.
- Preserve current testability and Docker workflows.
- Keep migrations explicit and reversible.
- Add structured logging for any runtime-policy decisions.

## Source-of-truth docs for this task

Read and follow these documents in this order:

1. `docs/runtime-zero-ai/ARCHITECTURE.md`
2. `docs/runtime-zero-ai/IMPLEMENTATION_PLAN.md`
3. `docs/runtime-zero-ai/TASK_BREAKDOWN.md`
4. `docs/runtime-zero-ai/ACCEPTANCE_CRITERIA.md`

## Required deliverables

### 1) Discovery → published runtime mapping lifecycle
Add a durable source mapping lifecycle with at least these concepts:
- draft mapping
- published runtime mapping
- mapping version / activation
- mapping stale flag

### 2) Deterministic runtime crawl path
For published sources, use deterministic URL classification and selector/regex extraction only.

### 3) Runtime AI policy enforcement
Add explicit guards so runtime jobs cannot call AI. If an AI-enabled code path is accidentally invoked for a published source runtime job, fail fast with a clear log and state transition instead of silently spending tokens.

### 4) Review/remapping path
Unknown or low-confidence pages must be marked for review/remapping instead of using AI fallback.

### 5) Hash-based skip / reprocess behavior
Use stored page content hashes to avoid reprocessing unchanged pages.

### 6) Drift detection
Track selector hit rate or equivalent extraction-quality signals and mark mappings stale when template drift is detected.

### 7) Tests
Add or update tests covering:
- discovery can produce a runtime mapping
- published runtime crawl uses no AI calls
- unknown pages are queued for review
- unchanged pages are skipped via hash
- drift signals mark a source mapping stale

## Implementation style

- Make small, coherent commits.
- Prefer feature flags or source-level policy objects over global behavior changes where practical.
- Keep old behavior available only for manual/admin flows if needed, but not for normal published-source runtime jobs.
- Add concise comments where policy boundaries matter.

## Files likely to change

Expect changes in at least these areas:
- `app/pipeline/runner.py`
- `app/crawler/automated_crawler.py`
- `app/crawler/site_structure_analyzer.py`
- `app/source_mapper/*`
- `app/db/models.py`
- migrations
- API routes / schemas for source mapping lifecycle
- tests

## Working rules

- Before changing behavior, inspect existing callers and job entry points.
- Do not assume that current “enrichment” jobs are safe; verify and retrofit them.
- When a choice exists, prefer deterministic execution over model inference.
- When deterministic execution is insufficient, queue for review/remap rather than improvising.

## Done definition

The work is complete only when a published source can be crawled repeatedly with zero OpenAI calls and the system surfaces review/remap states instead of spending runtime AI tokens.
