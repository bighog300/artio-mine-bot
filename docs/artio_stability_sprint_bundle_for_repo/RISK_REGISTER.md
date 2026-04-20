# Risk Register

## Risk 1 — Broken migration history blocks deploys
Impact: High
Likelihood: High
Why:
- a failed Prisma migration can block all subsequent migrations with P3009

Mitigation:
- repair migration SQL
- validate migration chain from zero
- document recovery path

## Risk 2 — CI gives false confidence
Impact: High
Likelihood: Medium
Why:
- passing typecheck/lint alone does not prove schema or route behavior is safe

Mitigation:
- require migration smoke test
- require supported tests
- improve failure diagnostics

## Risk 3 — Tests fail for environment reasons, not code reasons
Impact: High
Likelihood: High
Why:
- path alias or Next.js runtime mismatch can invalidate test signal

Mitigation:
- standardize test runner
- align environment with app runtime
- document authoritative commands

## Risk 4 — Regressions in shipped critical flows
Impact: High
Likelihood: Medium
Why:
- reminders, gallery saving, creator publishing, and scheduling were delivered recently

Mitigation:
- add focused regression coverage
- prioritize route and flow-level tests

## Risk 5 — Recovery remains tribal knowledge
Impact: Medium
Likelihood: High
Why:
- migration/deploy recovery steps are often undocumented

Mitigation:
- add repo docs for migration failure recovery and deploy checks
