# Codex Brief — Implement Job Runtime Visibility

Implement job runtime visibility for operators in this repository.

## Why
Operators can currently see job status snapshots and logs, but not what a running job is actively doing. We need live-ish execution visibility in the admin UI.

## Existing relevant files
Backend:
- `app/db/models.py`
- `app/db/crud.py`
- `app/api/routes/operations.py`
- `app/api/routes/logs.py`
- `app/pipeline/runner.py`
- `app/pipeline/backfill_processor.py`

Frontend:
- `frontend/src/pages/Jobs.tsx`
- `frontend/src/pages/Queues.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/App.tsx`

## Required deliverables

### Backend
1. Extend `Job` with:
   - `current_stage`
   - `current_item`
   - `progress_current`
   - `progress_total`
   - `last_heartbeat_at`
   - `last_log_message`
   - `metrics_json`

2. Add `JobEvent` model/table for operator timeline entries.

3. Add CRUD helpers:
   - `update_job_progress`
   - `append_job_event`
   - `list_job_events`

4. Add API endpoints:
   - extend `GET /jobs`
   - `GET /jobs/{job_id}`
   - `GET /jobs/{job_id}/events`

5. Instrument:
   - `app/pipeline/runner.py`
   - `app/pipeline/backfill_processor.py`

Persist meaningful stage/progress updates while jobs run.

### Frontend
1. Extend job types and API functions in `frontend/src/lib/api.ts`.
2. Upgrade `frontend/src/pages/Jobs.tsx` to show:
   - stage
   - current item
   - progress
   - heartbeat/stale state
   - link to detail
3. Add a job detail page or drawer with:
   - summary
   - progress
   - timeline
   - latest error
4. Improve `frontend/src/pages/Queues.tsx` with small derived runtime indicators.

## Constraints
- Keep changes aligned with the repo’s existing patterns.
- Do not introduce a heavy new framework.
- Prefer incremental additions over rewriting the job system.
- Preserve existing retry/pause/resume/cancel behavior.
- Keep API responses backward compatible where reasonable.

## Acceptance criteria
- Operators can see what a running job is doing from the Jobs page.
- Operators can open a single job and view a timeline of events.
- Active jobs expose heartbeat/progress fields.
- Backfill and pipeline jobs report meaningful stages.
- Existing app builds and migrations run cleanly.

## Implementation references
Use the spec files in this folder:
- `docs/codex/job-runtime-visibility/01-overview.md`
- `docs/codex/job-runtime-visibility/02-backend-spec.md`
- `docs/codex/job-runtime-visibility/03-frontend-spec.md`
- `docs/codex/job-runtime-visibility/04-implementation-plan.md`

## Output expectations
Please implement the code, migration, and minimal tests where practical.
