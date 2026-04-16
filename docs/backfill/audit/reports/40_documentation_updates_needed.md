# Documentation Updates Needed

## Phase docs to update

- [ ] `docs/backfill/phases/PHASE_1_FOUNDATION.md`
  - Align CLI section with implemented commands in `app/cli/backfill.py`.
  - Note that API routes are implemented in `app/api/routes/backfill.py`.

- [ ] `docs/backfill/phases/PHASE_2_WORKER.md`
  - Confirm worker function names (`enqueue_backfill_campaign`, `process_backfill_job`, `check_campaign_completion`).
  - Add progress emission and error handling notes from processor code.

- [ ] `docs/backfill/phases/PHASE_3_SCHEDULING.md`
  - Confirm schedule/policy models and route paths for schedules.
  - Document scheduler tick behavior and enable/disable semantics.

- [ ] `docs/backfill/phases/PHASE_4_DASHBOARD.md`
  - Replace missing component references with actual UI structure (`frontend/src/pages/Backfill.tsx`, shared layout/nav).
  - Document actual frontend API client usage.

## New docs to add

- [ ] `docs/backfill/api/endpoints.md` (source of truth from `app/api/routes/backfill.py`)
- [ ] `docs/backfill/api/models.md` (tables/models from `app/db/models.py`)
- [ ] `docs/backfill/guides/troubleshooting.md` (db/containerless audit tips)

## General cleanup

- [ ] Keep generated reports under `docs/backfill/audit/reports/`.
- [ ] Remove stale references to `/home/craig/artio-mine-bot` and use repository-relative paths.

---

## Update Completed (April 16, 2026)

- ✅ Rewrote `docs/backfill/phases/PHASE_4_DASHBOARD.md` to match the actual page-based implementation.
- ✅ Added implementation audit report: `docs/backfill/audit/reports/50_phase4_actual_implementation.md`.
- ✅ Confirmed real routing: `/backfill` in `frontend/src/App.tsx`.
- ✅ Confirmed real navigation entry in `frontend/src/components/shared/Layout.tsx`.
- ✅ Backed up original doc: `docs/backfill/phases/PHASE_4_DASHBOARD.md.backup`.
