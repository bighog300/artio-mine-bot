# MASTER CODEX PROMPT — STABILITY SPRINT

You are implementing the **Stability Sprint** for the Artio repository.

## Mission
Stabilize the repository after major feature delivery.

This sprint is not about expanding product scope.
It is about making the current system:
- safer to migrate
- safer to test
- safer to merge
- safer to deploy

## Primary goals
1. Fix Prisma migration reliability
2. Harden CI
3. Standardize test execution and environment reliability
4. Add regression protection for critical product loops
5. Improve deploy safety and recovery documentation

## Strict non-goals
Do not add new user-facing product features unless strictly necessary to complete the stability work.
Do not redesign core UX.
Do not rebuild recommendation logic.
Do not add admin/moderation product scope.
Do not start a new feature phase.

## Mandatory first step
Create these files before changing code:
- `REPO_STABILITY_AUDIT.md`
- `STABILITY_EXECUTION_CHECKLIST.md`

## In `REPO_STABILITY_AUDIT.md`, document:
1. Current Prisma migration health
2. Current CI workflows and gaps
3. Current test commands and failure modes
4. Which checks are missing for merge confidence
5. Which completed product loops lack regression coverage
6. Any deploy-specific risks already visible in the repo

Classify findings as:
- implemented
- partial
- missing
- broken

## Execution order
You must work in this order:
1. Repo audit
2. Execution checklist
3. Prisma migration fix and validation
4. CI migration smoke test
5. Test-runner hardening
6. Regression test coverage for critical flows
7. Deploy/recovery documentation
8. Validation and final report

Do not skip ahead unless you document a blocker in `REPO_STABILITY_AUDIT.md`.

## Repo-specific context
The known current blocker is the failed Prisma migration:
`20270420120000_sprint1_core_user_loop`

Known likely root causes:
- migration assumes `UserNotificationPrefs` already exists
- `EventReminder.id` SQL definition does not match Prisma schema default expectations
- failed migration state can trigger Prisma P3009 and block later migrations

Your job is to confirm the exact cause in the repo and fix it safely.

## Required work

### 1. Prisma migration safety
You must:
- inspect and fix the Sprint 1 migration
- align migration SQL with `prisma/schema.prisma`
- verify the full migration chain applies on a clean database
- ensure no failed migration blocks later migrations in CI

Expected deliverables:
- corrected migration SQL
- migration validation notes
- recovery guidance if failed state exists in shared environments

### 2. CI hardening
You must:
- add or improve a migration smoke test on a fresh database
- make sure CI runs:
  - prisma validate
  - prisma generate
  - prisma migrate deploy
  - typecheck
  - lint
  - tests
- improve failure output so migration issues are diagnosable from logs

### 3. Test environment hardening
You must:
- identify current route/integration test failures caused by environment mismatch
- standardize one reliable test execution path
- fix path alias / module resolution issues if present
- make tests fail for real regressions, not tooling confusion

### 4. Regression protection
Add or improve automated coverage for these product-critical areas:
- event reminder flow
- notification preferences
- gallery save flow
- creator gallery publish flow
- scheduled publish flow

Coverage can be unit, integration, or route-level smoke coverage, but it must be meaningful.

### 5. Deploy safety and recovery
You must add documentation for:
- migration failure recovery
- when to use `prisma migrate resolve`
- when to reset an ephemeral DB
- how to inspect `_prisma_migrations`
- what checks must pass before merge/deploy

## Acceptance criteria
You must validate against all of the following:

- Sprint 1 migration applies on a clean database
- CI contains a migration smoke test
- CI failure output is more actionable for migration issues
- One supported test path is documented and working
- Critical product loops have regression protection
- Migration/deploy recovery docs exist in the repo
- No unrelated feature scope was added

## Required final report
When finished, provide:
1. Summary of root causes found
2. Exact files added/modified
3. What changed in the Sprint 1 migration
4. What CI checks were added/changed
5. What test environment issues were fixed
6. What regression tests were added
7. How to validate the repo end-to-end
8. Which acceptance criteria are complete/partial/blocked
9. Any remaining operational risk

## Definition of done
This sprint is done when:
- the repo is migration-safe
- CI gives trustworthy merge signal
- tests run in a stable environment
- critical shipped features are covered against regression
- recovery steps are documented
