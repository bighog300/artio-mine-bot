# Artio Handoff: Next Execution Steps

## Current State
- User UX bundle: IMPLEMENTED
- Creator UX bundle: IMPLEMENTED
- Product loops: COMPLETE
- Repo: FUNCTIONALLY COMPLETE BUT NOT STABLE
- Blocking issue: Prisma migration failure (Sprint 1)

---

## Objective for Next GPT
Execute a **Stability Sprint** with strict order:

1. Verify bundles (user + creator)
2. Lock acceptance criteria
3. Fix migration (critical)
4. Harden CI
5. Add regression protection

---

## STEP 1 — Verify User & Creator Bundles

### Goal
Confirm that implementation still matches product contracts.

### Actions
- Read:
  - /docs/product/user-experience.md
  - /docs/product/creator-experience.md
  - /docs/product/acceptance-criteria.md

- For each core flow, verify:

#### User
- Discover → Save → Remind → Return works end-to-end
- Notification preferences persist and apply
- Saved hub reflects correct data
- Feed mixes events + galleries

#### Creator
- Gallery flow:
  draft → preview → publish → schedule → archive
- Event publish includes preview + validation
- Public creator page shows:
  - events
  - galleries
- Analytics show usable metrics

### Output
Create:
- BUNDLE_VERIFICATION_REPORT.md

Mark each:
- complete
- partial
- broken

---

## STEP 2 — Lock Acceptance Criteria

### Goal
Turn product docs into enforceable rules

### Actions
- Extract critical flows into testable assertions
- Ensure they exist in:
  - tests/
  - or create them if missing

Minimum:
- reminder flow test
- gallery save test
- creator publish test
- scheduled publish test

---

## STEP 3 — FIX MIGRATION (CRITICAL BLOCKER)

### Problem
Migration:
20270420120000_sprint1_core_user_loop

Issues:
- assumes UserNotificationPrefs exists
- EventReminder.id missing DB default
- causes Prisma P3009

### Actions
1. Inspect:
   prisma/migrations/20270420120000_sprint1_core_user_loop/migration.sql

2. Fix:
- Ensure UserNotificationPrefs is created if missing
- Align EventReminder.id with Prisma schema
- Ensure safe execution on clean DB

3. Validate:
pnpm prisma migrate deploy

4. If DB is stuck:
pnpm prisma migrate resolve --rolled-back 20270420120000_sprint1_core_user_loop

(only after verifying DB state)

### Output
- MIGRATION_FIX_REPORT.md

---

## STEP 4 — HARDEN CI

### Goal
Make CI trustworthy

### Required checks:
- install
- prisma validate
- prisma generate
- prisma migrate deploy (fresh DB)
- typecheck
- lint
- tests

### Add:
- migration smoke test job
- better failure logs

---

## STEP 5 — STABILIZE TEST ENVIRONMENT

### Problem
Tests failing due to environment mismatch

### Fix:
- align Next.js test setup
- fix path aliases
- define ONE official test command

---

## STEP 6 — ADD REGRESSION PROTECTION

### Must cover:
- reminders
- notification preferences
- gallery save
- creator gallery publish
- scheduled publishing

---

## EXECUTION ORDER (DO NOT CHANGE)

1. Bundle verification
2. Acceptance locking
3. Migration fix
4. CI hardening
5. Test stabilization
6. Regression coverage

---

## Definition of Done

- Migration runs on clean DB
- CI is green
- Tests are reliable
- Core flows protected
- Bundles verified against reality

---

## Final Instruction

Do NOT:
- add new features
- refactor unrelated code
- start new phase

Focus ONLY on:
**stability + correctness + enforcement**
