# AI Source Mapper — Implementation Document Set

This folder contains the full implementation pack for the **AI Source Mapper** enhancement.

## Documents

1. [`PRD.md`](./PRD.md)
   Product requirements, user goals, workflows, constraints, and acceptance criteria.

2. [`UX_ADMIN_WORKFLOWS.md`](./UX_ADMIN_WORKFLOWS.md)
   Admin journeys, information architecture, matrix behavior, drag-and-drop interactions, and preview UX.

3. [`TECHNICAL_DESIGN.md`](./TECHNICAL_DESIGN.md)
   Backend and frontend architecture, service boundaries, job flow, and component/file plan.

4. [`API_CONTRACTS.md`](./API_CONTRACTS.md)
   Proposed request/response contracts for scan, mapping, preview, publish, and moderation APIs.

5. [`DATA_MODEL_AND_MIGRATIONS.md`](./DATA_MODEL_AND_MIGRATIONS.md)
   Proposed entities, SQLAlchemy models, indexes, lifecycle states, and Alembic migration plan.

6. [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md)
   Phased delivery plan with concrete repo file changes, milestones, and sequencing.

7. [`TEST_PLAN.md`](./TEST_PLAN.md)
   Backend, frontend, integration, and UAT coverage for a safe rollout.

## Recommended implementation order

1. Data model and migrations
2. Backend scan + mapping proposal APIs
3. Preview and sample extraction pipeline
4. Admin matrix UI
5. Drag-and-drop editing
6. Publish / versioning / rollback
7. Feedback learning and rescan diffing

## Scope summary

The feature adds an admin flow where an operator pastes a source URL, runs an AI-assisted scan, reviews proposed field mappings in a matrix, edits mappings inline or by drag and drop, previews exactly where data will be stored and categorized, and publishes the mapping set for live ingestion.

## Design principles

- Never auto-publish AI mappings without admin approval.
- Every mapping must be previewable against real page samples.
- Schema destinations must stay explicit and auditable.
- Mapping changes must be versioned and reversible.
- Optional advanced automation should not remove human moderation.
