# Implementation plan

## Objective

Front-load AI token spend into a one-time discovery/remapping flow, then execute all normal mining runs autonomously with deterministic runtime rules.

## Phase 1 — Policy and schema foundations

### Changes
- Add source-level runtime fields and mapping lifecycle state.
- Add a versioned mapping entity if needed.
- Add page metadata fields for content hash, extraction/classification method, review reason, and mapping version used.
- Add job-level or run-level counters for discovery vs runtime AI token accounting.

### Outcome
The data model can represent draft mappings, published mappings, deterministic runtime state, and drift/review states.

## Phase 2 — Discovery output becomes publishable runtime mapping

### Changes
- Extend discovery/site analysis output so it generates a complete mapping draft.
- Add compile/publish step that converts a draft mapping into a runtime mapping contract.
- Store both raw draft and compiled runtime mapping JSON.

### Outcome
Discovery can produce everything needed for deterministic runtime without requiring later AI extraction.

## Phase 3 — Deterministic runtime executor becomes default for published sources

### Changes
- Route normal runtime crawl jobs for published sources through deterministic execution.
- Prefer `app/crawler/automated_crawler.py` or equivalent as the runtime execution engine.
- Ensure URL classification, selector extraction, follow rules, and asset collection run only from the published mapping.

### Outcome
Published sources crawl and extract without model calls.

## Phase 4 — Runtime AI guardrails

### Changes
- Add explicit runtime AI policy object or guard.
- Enforce it in all runtime job entrypoints.
- Enforce it before any calls to AI classifier or AI extractors.
- Fail closed: if runtime reaches an AI path, convert to review state or raise a clear exception.

### Outcome
It becomes structurally difficult for runtime jobs to spend tokens accidentally.

## Phase 5 — Hash-based skip and deterministic reprocessing

### Changes
- Compute/store content hash for fetched HTML.
- Skip runtime extraction if page content hash and mapping version are unchanged.
- Keep raw page snapshots available for deterministic reprocessing when mappings improve.

### Outcome
Unchanged pages do not consume unnecessary compute or create duplicate extraction work.

## Phase 6 — Review queue and drift detection

### Changes
- Replace runtime AI fallback with deterministic review outcomes:
  - `unmapped_page_type`
  - `low_confidence_extraction`
  - `selector_miss`
  - `mapping_stale`
- Track extraction-quality metrics and mark mapping stale on template drift.

### Outcome
The system handles failure by queuing review/remapping instead of spending tokens.

## Phase 7 — API/UI surface area

### Changes
Add or adapt endpoints for:
- creating discovery runs
- listing mapping versions
- publishing a mapping version
- viewing runtime mapping status / stale flags
- viewing review queue / review reasons

### Outcome
Operators can manage the discovery → publish → runtime lifecycle explicitly.

## Phase 8 — Tests and rollout

### Changes
- Add unit/integration tests for policy, mapping lifecycle, runtime enforcement, hashing, and drift detection.
- Add logs/metrics proving zero runtime AI usage.

### Outcome
The retrofit is measurable and safe to ship.

## Suggested implementation order by code area

1. models + migration
2. mapping version persistence
3. runtime policy object / guardrails
4. deterministic runtime routing
5. hash skip logic
6. review queue states
7. drift detection
8. API/UI exposure
9. tests and docs

## Specific retrofit guidance

### `app/pipeline/runner.py`
- Add source/job routing so published runtime sources bypass AI-heavy extraction.
- Prevent `run_enrichment_existing_pages()` from invoking AI for deterministic runtime sources.
- Convert unsupported cases to review/remap states.

### `app/crawler/automated_crawler.py`
- Promote this path to the primary runtime execution engine.
- Ensure it reads from the published runtime mapping.
- Remove or hard-disable runtime AI fallback for published runtime jobs.

### `app/crawler/site_structure_analyzer.py`
- Expand output so it can generate a complete runtime mapping draft.
- Keep AI usage limited to discovery/remapping.

### `app/source_mapper/*`
- Add draft/publish/version workflow.
- Compile mapping draft into runtime JSON.

### AI modules
- Keep `app/ai/classifier.py` and `app/ai/extractors/*` available for discovery/manual tools only.
- Add guardrails so runtime cannot call them when `ai_allowed == false`.
