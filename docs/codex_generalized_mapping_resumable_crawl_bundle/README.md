# Codex Execution Bundle: Generalized Source Mapping + Resumable Crawl Engine

This bundle is a repo-ready execution package for evolving the platform from
source-specific crawling into a generalized adaptive mapping and resumable mining system.

## Primary outcome

Enable the system to:
- ingest many different site structures
- infer candidate page families and mapping strategies
- present mapping options to an admin for approval
- execute crawls against approved mappings
- persist crawl frontier and checkpoints
- resume crawls from prior progress
- keep mining fresh over time with incremental recrawls and drift detection

## Recommended repo placement

/docs/codex/generalized-mapping-resumable-crawl/

## Execution order

1. `PHASE_PLAN.md`
2. `TASKS.yaml`
3. `CODEX_PROMPT.md`
4. `ARCHITECTURE.md`
5. `DATA_MODEL.md`
6. `UI_WORKFLOW.md`
7. `RESUME_AND_FRESHNESS.md`
8. `DRIFT_DETECTION.md`
9. `IMPLEMENTATION_CHECKLIST.md`
10. `TEST_PLAN.md`

## Scope boundaries

This bundle focuses on:
- generalized site profiling
- mapping suggestion
- admin mapping approval
- durable crawl frontier
- resumable crawl execution
- incremental freshness recrawls
- mapping versioning and drift detection

This bundle does not require:
- a full extraction-engine rewrite first
- SSL/TLS changes
- large frontend redesign outside mapper/admin workflows

## Non-negotiable principles

- deterministic signals first
- LLM assistance only where ambiguity warrants it
- admin approval before a source mapping becomes active
- durable state for crawls and frontier
- no one-shot-only crawling
- explicit mapping versions
- observable reasons for inclusion, exclusion, and drift
