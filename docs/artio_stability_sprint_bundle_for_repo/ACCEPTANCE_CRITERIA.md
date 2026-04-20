# Acceptance Criteria

The stability sprint is complete when all of the following are true:

1. The Sprint 1 Prisma migration applies on a clean database.
2. `pnpm prisma migrate deploy` succeeds in CI on a fresh DB.
3. Migration failure output is actionable enough to diagnose from CI logs.
4. The repo has one documented, supported test path for route/integration execution.
5. Critical loops have automated regression protection:
   - reminders
   - notification preferences
   - gallery save
   - creator gallery publish
   - scheduled publish
6. Recovery documentation exists for failed migrations and deploy issues.
7. No unrelated product scope was added during the sprint.

## Evidence expected
- CI config changes
- migration SQL fix
- audit/checklist files
- test files or test-runner config changes
- recovery doc
- final validation notes
