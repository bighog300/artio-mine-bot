# Stability Execution Checklist

## Repo audit
- [ ] Create `REPO_STABILITY_AUDIT.md`
- [ ] Identify migration chain risks
- [ ] Identify CI workflow gaps
- [ ] Identify test-runner problems
- [ ] Identify missing regression coverage

## Migration safety
- [ ] Fix Sprint 1 migration SQL
- [ ] Align SQL with Prisma schema
- [ ] Validate full migration chain on clean DB
- [ ] Document whether `migrate resolve` is ever required and when

## CI hardening
- [ ] Add migration smoke test job
- [ ] Ensure prisma validate/generate/deploy are in CI
- [ ] Ensure typecheck/lint/tests are in CI
- [ ] Improve failure logging

## Test environment
- [ ] Standardize authoritative test command(s)
- [ ] Fix path alias/module resolution issues
- [ ] Ensure route/integration tests run in the correct environment

## Regression protection
- [ ] Reminder flow covered
- [ ] Notification preferences covered
- [ ] Gallery save flow covered
- [ ] Creator gallery publish flow covered
- [ ] Scheduled publish flow covered

## Documentation
- [ ] Add migration recovery doc
- [ ] Add validation notes or deploy notes

## Validation
- [ ] `pnpm prisma validate`
- [ ] `pnpm prisma generate`
- [ ] `pnpm prisma migrate deploy`
- [ ] `pnpm typecheck`
- [ ] `pnpm lint`
- [ ] tests
- [ ] final acceptance checklist updated
