# Artio Stability Sprint Bundle

This bundle is a repo-ready handoff for the next sprint after completing Phases 1–3.

## Purpose
Stabilize Artio after major feature delivery by focusing on:
- migration safety
- CI reliability
- test runner correctness
- deployment safety
- regression protection for the completed product loops

## Why this sprint exists
Artio now has strong product coverage across:
- user core loop
- gallery discovery
- creator publishing

The main risk has shifted from missing features to operational instability, especially:
- Prisma migration failure in Sprint 1 migration history
- weak CI confidence for schema/deploy changes
- inconsistent test environment reliability
- insufficient regression protection for critical flows

## Included
- MASTER_CODEX_PROMPT.md
- SPRINT_GOALS.md
- STABILITY_SCOPE.md
- BACKLOG_BY_PRIORITY.md
- ACCEPTANCE_CRITERIA.md
- EXECUTION_CHECKLIST_TEMPLATE.md
- RISK_REGISTER.md
- VALIDATION_PLAN.md
- HANDOFF_INSTRUCTIONS.md

## Sprint objective
Ship a stability-first sprint that makes Artio safer to merge, safer to deploy, and easier to recover when something breaks.
