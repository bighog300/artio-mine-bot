# Stability Scope

## In scope

### Migration safety
- audit migration chain
- repair broken Sprint 1 migration
- verify schema/migration alignment
- validate clean-db deploy path

### CI hardening
- fresh Postgres migration smoke test
- required checks for merge confidence
- better logging for migration failures

### Test reliability
- route/integration runner correctness
- path alias and framework environment alignment
- documented authoritative test path

### Regression protection
- reminder flow
- gallery save/discovery flow
- creator gallery publish flow
- scheduled publish flow
- notification preference persistence

### Documentation
- migration recovery guide
- CI/deploy validation notes

## Out of scope
- new feature delivery
- recommendation redesign
- creator UX redesign
- admin/moderation changes
- major architecture rewrite
