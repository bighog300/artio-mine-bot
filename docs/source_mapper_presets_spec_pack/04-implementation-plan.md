# Source Mapper Presets — Implementation Plan

## Phase 1 — Data model and migration

- Add `source_mapping_presets`
- Add `source_mapping_preset_rows`
- Add indexes and FK cascade behavior
- Create Alembic migration with unique revision ID

## Phase 2 — Backend CRUD and API

- Add CRUD/service helpers
- Add request/response schemas
- Add new routes:
  - list presets
  - create preset
  - delete preset
- Validate source ownership and origin version relationships

## Phase 3 — Frontend integration

- Add API client methods
- Add presets panel to mapper page
- Add create preset dialog
- Add delete action with confirmation
- Refresh preset list after mutations

## Phase 4 — Validation and polish

- Ensure approved-only default works
- Handle zero-row creation attempts gracefully
- Show row counts and origin version in UI
- Verify preset delete cascades rows correctly

## Recommended implementation order

1. backend schema + migration
2. backend CRUD
3. backend routes + schemas
4. frontend API methods
5. frontend presets panel
6. create/delete flows
7. tests
