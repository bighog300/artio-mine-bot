You are implementing the next major workstream in this repository:

**Generalized Source Mapping + Resumable Crawl Engine**

## Objective

Move the platform from source-specific mapping/crawling to a generalized system that can:
- inspect previously unseen sites
- infer candidate page families and mapping strategies
- present mapping options to an admin for approval
- crawl using approved mappings
- persist crawl frontier and checkpoints
- resume from previous progress
- stay fresh over time with incremental recrawls and drift detection

## Execute in this order

1. site profiler and URL family clustering
2. mapping suggestion engine
3. admin mapping approval workflow
4. durable frontier and resumable crawling
5. incremental freshness recrawls
6. drift detection and mapping versioning

## Rules

- implement phase by phase
- add tests with every phase
- prefer deterministic logic before LLM usage
- require admin approval before a draft mapping becomes active
- do not build one-shot-only crawl logic
- preserve existing working crawl paths unless intentionally upgrading them
- use migrations for new persistence models
- keep changes reviewable and modular

## Primary files/docs to follow

- `README.md`
- `PHASE_PLAN.md`
- `ARCHITECTURE.md`
- `DATA_MODEL.md`
- `UI_WORKFLOW.md`
- `RESUME_AND_FRESHNESS.md`
- `DRIFT_DETECTION.md`
- `IMPLEMENTATION_CHECKLIST.md`
- `TEST_PLAN.md`

## High-priority implementation details

### Site profiler
Build a profiler that samples a source and outputs:
- discovered entrypoints
- URL family clusters
- representative samples
- candidate page types and confidence

### Mapping suggestion
Generate family-level suggestions:
- page type
- include/exclude
- follow links
- pagination mode
- crawl priority
- freshness policy

### Admin approval
Allow operators to:
- inspect families
- override suggestions
- publish an approved mapping version
- start a crawl from the approved mapping

### Durable frontier
Persist:
- normalized URLs
- statuses
- retry metadata
- last fetched / next eligible fetch
- content hash
- mapping version attribution

### Resume
Resume should continue from frontier state, not restart discovery from the seed URL.

### Drift
Detect:
- null-rate spikes
- new uncovered families
- mapping degradation
- and propose remap drafts

## Constraints

- do not weaken security/auth
- do not hardcode source-specific logic as the primary strategy
- avoid broad speculative refactors unrelated to this workstream
- keep the UI practical: wizard first, advanced studio later
- preserve observability and explainability

## Deliverables per phase

For each phase, provide:
1. summary of what was built
2. files changed
3. migrations added
4. tests added
5. known follow-ups before next phase

Start with Phase 1 only unless the codebase and tests make Phase 2 a natural continuation in the same pass.
