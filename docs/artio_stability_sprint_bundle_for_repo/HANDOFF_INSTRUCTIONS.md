# Handoff Instructions

Give this bundle to Codex together with:
- the current Artio repository
- the CI hardening plan
- the known Prisma migration failure logs
- any current workflow YAML files

## Recommended instruction
"Execute this as a stability sprint only. Start with the repo audit and checklist, then fix migration safety before touching CI or tests. Do not add new product features."

## Recommended review cadence
- after repo audit
- after migration fix
- after CI workflow update
- after regression tests
- after final validation

## Artifacts Codex should create in the repo
- `REPO_STABILITY_AUDIT.md`
- `STABILITY_EXECUTION_CHECKLIST.md`
- `docs/ci/migration-recovery.md` or equivalent
- any CI workflow updates
- final validation notes
