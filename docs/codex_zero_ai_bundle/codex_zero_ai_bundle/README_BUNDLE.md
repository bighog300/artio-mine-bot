# Codex bundle: zero-AI runtime mining

This bundle is intended to be committed into the repository so Codex can implement the new architecture safely and incrementally.

## Important

The current repository-level `AGENTS.md` describes the original scaffold/build order for the project. It is now stale for this task and will bias Codex toward the wrong objective.

For this implementation, replace the repo's current `AGENTS.md` with the bundled `AGENTS.md`, or paste the bundled execution prompt into Codex and explicitly tell it to follow the bundled docs instead of the existing scaffold instructions.

## Recommended placement in the repo

- `AGENTS.md` → replace repo root AGENTS.md temporarily for this implementation
- `docs/runtime-zero-ai/ARCHITECTURE.md`
- `docs/runtime-zero-ai/IMPLEMENTATION_PLAN.md`
- `docs/runtime-zero-ai/TASK_BREAKDOWN.md`
- `docs/runtime-zero-ai/ACCEPTANCE_CRITERIA.md`
- `CODEX_EXECUTION_PROMPT.md`

## What this bundle covers

- one-time AI-assisted discovery and mapping
- strict zero-AI runtime crawl and extraction
- deterministic extraction from published source mappings
- mapping drift detection and remapping workflow
- phased implementation sequence with acceptance criteria
