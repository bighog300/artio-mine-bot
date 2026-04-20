# Backlog by Priority

## P0 — Must fix now
- Repair `20270420120000_sprint1_core_user_loop` migration
- Verify full migration chain on fresh DB
- Add CI migration smoke test
- Document migration recovery steps
- Stabilize test runner if it is blocking trustworthy CI

## P1 — Strongly recommended
- Add regression tests for reminder flow
- Add regression tests for gallery save flow
- Add regression tests for creator gallery publish flow
- Add regression tests for scheduled publish flow
- Improve migration failure diagnostics in CI

## P2 — Good next improvements
- Split CI into fast and slow lanes
- Add CI summary output
- Add PR template for schema/deploy-risk changes
- Add CODEOWNERS for Prisma/workflows/cron areas
