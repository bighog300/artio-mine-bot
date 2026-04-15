# AI Source Mapper — Implementation Plan

## 1. Delivery strategy

Ship in phases so each milestone is independently testable and deployable.

## 2. Phase 0 — Design and scaffolding

### Goals
- add data model scaffolding
- add API schema placeholders
- add frontend route skeletons

### Files to create or modify

#### Backend
- `app/db/models.py`
- `app/db/crud.py`
- `app/api/schemas.py`
- new `app/api/routes/source_mapper.py`
- `app/api/main.py`
- `app/db/migrations/versions/*_source_mapper_tables.py`

#### Frontend
- `frontend/src/lib/api.ts`
- `frontend/src/App.tsx`
- new `frontend/src/pages/SourceMapping.tsx`
- new `frontend/src/components/source-mapper/*`

### Deliverables
- migration merged
- empty draft/list endpoints working
- route visible in UI

## 3. Phase 1 — Scan draft creation and page-type discovery

### Backend
Implement:
- create mapping draft endpoint
- enqueue scan job
- fetch sample pages
- page-type clustering
- page-type summaries

### Frontend
Implement:
- scan setup form
- scan status polling
- page-type sidebar

### Acceptance
- admin can create draft and see detected page types for a source

## 4. Phase 2 — Mapping proposal generation and matrix UI

### Backend
Implement:
- mapping row generation
- list/update row endpoints
- bulk actions
- validation for destination entity/field

### Frontend
Implement:
- mapping matrix table
- inline row editor
- filters and sorting
- bulk approve/reject

### Acceptance
- admin can moderate mapping rows without leaving the page

## 5. Phase 3 — Preview and sample extraction review

### Backend
Implement:
- preview endpoint
- sample run endpoint
- sample result storage

### Frontend
Implement:
- preview drawer or side panel
- sample extraction review table
- destination record preview cards

### Acceptance
- admin can see where extracted data will be stored before publish

## 6. Phase 4 — Publish, versioning, rollback

### Backend
Implement:
- publish endpoint
- version history endpoint
- rollback endpoint
- source active mapping version integration

### Frontend
Implement:
- version history panel
- publish confirmation modal
- rollback controls

### Acceptance
- published versions are immutable and rollback works

## 7. Phase 5 — Drag-and-drop and advanced moderation

### Backend
Likely minimal backend changes.

### Frontend
Implement:
- schema board
- drag-and-drop row reassignment
- ignored bucket
- conflict indicators

### Acceptance
- admin can move mapping targets by drag-and-drop with immediate preview updates

## 8. Phase 6 — Feedback learning and rescan diff

### Backend
Implement:
- admin feedback capture
- rescan diff generation
- optional selector stability scoring

### Frontend
Implement:
- feedback controls
- rescan comparison UI
- changed-from-published indicators

## 9. Integration notes

### Source onboarding
Update `Sources.tsx` add-source modal/button flow:
- `Save draft source`
- `Save and open mapping`
- optional `Save and run quick scan`

### Source detail
Add a `Mapping` tab to `SourceDetail.tsx` showing:
- active mapping version
- draft state
- scan status
- entry link to mapping workspace

### Mining pipeline integration
Before production mining extraction:
- load `active_mapping_version_id`
- if present, use approved mappings
- if absent, fall back to existing extraction rules behavior

## 10. Suggested tickets

### Backend tickets
1. Add source mapper tables and migrations
2. Add mapping draft CRUD + schemas
3. Add scan queue job and discovery service
4. Add page-type clustering and summary response
5. Add mapping row proposal generation
6. Add preview endpoint
7. Add sample run review endpoints
8. Add publish/version history/rollback
9. Wire published mappings into mining extraction

### Frontend tickets
1. Add mapping route and API client types
2. Build scan setup form
3. Build page-type sidebar
4. Build mapping matrix with inline editing
5. Build preview panel
6. Build sample run review UI
7. Build version history/publish UI
8. Add drag-and-drop schema board

## 11. Definition of done

- migrations applied
- backend tests pass
- frontend build passes
- preview works on sample pages
- published mapping version can be used by mining
- admin can roll back to previous version
- no production records are created by preview/sample-run flows
