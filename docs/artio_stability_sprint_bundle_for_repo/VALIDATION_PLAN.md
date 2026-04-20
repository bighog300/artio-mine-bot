# Validation Plan

## Local validation
Run:
- `pnpm prisma validate`
- `pnpm prisma generate`
- `pnpm prisma migrate status`
- `pnpm prisma migrate deploy`
- `pnpm typecheck`
- `pnpm lint`
- authoritative test command(s)

## Clean DB validation
Use a fresh Postgres database and verify:
- full migration chain applies
- no failed migration remains
- schema aligns with Prisma models

## CI validation
Confirm:
- migration smoke test job passes
- typecheck passes
- lint passes
- supported tests pass
- logs are actionable on failure

## Product-level smoke validation
Manually or automatically verify:
- reminder create/delete still works
- notification preferences still persist
- gallery save still works
- creator can still publish/schedule gallery content
- scheduled publish route still works
