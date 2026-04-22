# Artio Mine Bot — Codex Implementation Bundle

## Scope
Implement fixes for the **mapping admin workflow** and the **records review/moderation workflow** in the uploaded repo.

This bundle is tailored to the current codebase layout:
- Main mapping workflow UI: `frontend/src/pages/SourceMapping.tsx`
- Legacy/secondary mapping UI: `frontend/src/pages/MappingReview.tsx`
- Mapping APIs: `app/api/routes/source_mapper.py`, `app/api/routes/mapping_presets.py`
- Mining readiness guard: `app/api/routes/mine.py`
- Records list/detail moderation UI: `frontend/src/pages/Records.tsx`, `frontend/src/pages/RecordDetail.tsx`
- Records API: `app/api/routes/records.py`
- Admin conflict review API: `app/api/routes/review.py`
- Shared frontend API layer: `frontend/src/lib/api.ts`

## What to fix

### 1) Unify and harden the mapping workflow

#### Findings from repo review
- `SourceMapping.tsx` is the real admin source-mapper flow and is wired to the modern backend endpoints.
- `MappingReview.tsx` still exists and has tests, but it appears to represent a parallel or older review workflow.
- This duplication creates operator confusion and makes it unclear which page is authoritative.
- Mining readiness in `app/api/routes/mine.py::_assert_source_mapping_ready` is currently too weak: it only checks for an active preset or published mapping version, not whether the resulting runtime map is actually usable.

#### Required changes
1. Make `SourceMapping.tsx` the single source of truth for mapping operations.
2. Audit `MappingReview.tsx` and do one of the following:
   - remove it and update routes/tests accordingly, or
   - redirect it into the `SourceMapping` route, or
   - keep it only if there is a confirmed active use case, but clearly mark it as legacy and prevent duplicate operator entry points.
3. Strengthen backend readiness checks in `app/api/routes/mine.py`:
   - require the source to exist,
   - require published/applicable mapping state,
   - require a non-empty `structure_map`,
   - require `crawl_plan.phases` to be non-empty,
   - require at least one usable extraction/page-type rule where applicable,
   - fail with a clear `422` if the source is not truly mine-ready.
4. Reflect readiness in the mapping UI:
   - disable actions that should not be available yet,
   - show clearer state badges/messages for draft, scanned, ready to publish, published, preset applied, mine-ready.
5. Preserve the existing sample-run review flow and mapping row moderation flow.

### 2) Harden mapping moderation behavior

#### Findings from repo review
- The mapping workflow supports row-level and bulk moderation via `rows/actions`.
- The sample-run review flow is implemented and tested.
- Current backend coverage is decent, but frontend safeguards and clarity can be improved.

#### Required changes
1. Ensure row bulk actions return consistent UI-refreshable summaries.
2. Ensure publish/create-preset/apply-preset buttons are disabled when prerequisites are not satisfied.
3. Improve messaging around low-confidence rows and publish blockers.
4. Keep current backend behavior that blocks invalid publish states; do not relax those constraints.

### 3) Tighten records moderation permissions and workflow

#### Findings from repo review
- `app/api/routes/records.py` currently exposes list, detail, approve, reject, bulk approve, edit, and set-primary-image endpoints.
- Unlike `review.py` and `source_mapper.py`, `records.py` does **not** currently use `require_permission(...)`.
- This means records moderation may be more open than intended.
- The frontend moderation pages exist in `Records.tsx` and `RecordDetail.tsx`.
- Backend tests cover approve/reject/bulk approve endpoints, but frontend moderation interactions need stronger coverage.

#### Required changes
1. Decide the intended permission model for records moderation and align `app/api/routes/records.py` with it.
   - If moderation is admin-only, add the appropriate RBAC dependency/dependencies.
   - Do not accidentally block read-only listing if that is intentionally broader.
2. Preserve and verify these moderation actions:
   - approve record,
   - reject record with reason,
   - edit record before/after moderation as allowed,
   - bulk approve with explicit guardrails.
3. Improve auditability where needed:
   - ensure audit entries include enough details for approve/reject/update actions,
   - keep rejection reason visible/persisted.
4. Improve frontend moderation UX:
   - consistent status chips,
   - clear success/error feedback,
   - reject-with-reason flow works from list and detail screens,
   - bulk actions require explicit confirmation if appropriate.

### 4) Improve moderation queue usability

#### Required changes
1. Verify `Records.tsx` supports filtering and sorting needed for a moderation queue.
2. Add or improve filters for:
   - pending/review status,
   - approved,
   - rejected,
   - source,
   - record type,
   - confidence band,
   - search.
3. Keep adjacent navigation in `RecordDetail.tsx` working.
4. Make it easy to move to the next pending record.

## Acceptance criteria

### Mapping
- There is one clearly authoritative mapping workflow in the UI.
- Legacy or duplicate mapping review entry points are removed, redirected, or clearly isolated.
- Publishing/applying presets still works.
- Starting mining fails early and clearly if the source has no usable runtime map.
- The mapping UI prevents invalid actions where possible.
- Existing sample-run and row moderation flows still work.

### Records moderation
- Approve and reject still work.
- Reject reason is preserved and visible where appropriate.
- Bulk approve still works, with clear safeguards.
- Record moderation permissions are explicit and intentional.
- Record moderation remains auditable.
- Records list/detail UI supports an efficient review queue.

## Files to inspect first
- `frontend/src/App.tsx`
- `frontend/src/pages/SourceMapping.tsx`
- `frontend/src/pages/MappingReview.tsx`
- `frontend/src/pages/Records.tsx`
- `frontend/src/pages/RecordDetail.tsx`
- `frontend/src/lib/api.ts`
- `app/api/routes/source_mapper.py`
- `app/api/routes/mapping_presets.py`
- `app/api/routes/mine.py`
- `app/api/routes/records.py`
- `app/api/routes/review.py`
- relevant tests in:
  - `tests/test_source_mapper_phase1.py`
  - `tests/test_api.py`
  - `frontend/src/pages/__tests__/MappingReview.test.tsx`

## Test expectations
Add or update tests for:

### Backend
- `mine.py::_assert_source_mapping_ready` rejects empty/unusable `structure_map`
- records moderation permissions behave as intended
- approve/reject/update/bulk approve still work after changes

### Frontend
- mapping route behavior if `MappingReview.tsx` is removed/redirected
- disabled/enabled mapping action buttons by workflow state
- record approve/reject interactions in list/detail views
- reject-reason handling

Run at minimum:
- `pytest -q tests/test_source_mapper_phase1.py tests/test_api.py`
- any newly added backend tests
- frontend tests for updated pages/components
- `npm -C frontend run build`

## Non-goals
- Do not rewrite the mining engine in this task.
- Do not change Alembic history.
- Do not remove art.co.za-specific mining logic unless necessary for these UI/admin fixes.

## Deliverables from Codex
1. Code changes in repo
2. Tests added/updated
3. Short implementation summary with:
   - root causes fixed
   - files changed
   - commands run
   - remaining risks
