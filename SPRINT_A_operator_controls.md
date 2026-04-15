# Sprint A: Operator Controls for Mining and Extraction

## Objective
Make the platform easier to operate by adding clear source-level controls for starting, pausing, resuming, stopping, and retrying mining runs.

## Scope

### Frontend
Update:
- `frontend/src/pages/Sources.tsx`
- `frontend/src/pages/SourceDetail.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/lib/api.ts`

Add:
- Source row action buttons:
  - Start Discovery
  - Start Full Mining
  - Pause
  - Resume
  - Stop
  - Retry Failed
- Source status badges:
  - idle
  - running
  - paused
  - stopping
  - failed
  - completed
- Source detail status card showing:
  - current status
  - current stage
  - active jobs
  - pages crawled
  - records created
  - last run started/finished
  - latest error

### Backend
Update:
- `app/api/routes/sources.py`
- `app/api/routes/operations.py`
- `app/api/routes/metrics.py`
- `app/api/schemas.py`
- `app/db/models.py`
- `app/db/crud.py`

Add or confirm endpoints:
- `POST /api/sources/{id}/start`
- `POST /api/sources/{id}/pause`
- `POST /api/sources/{id}/resume`
- `POST /api/sources/{id}/stop`
- `POST /api/sources/{id}/retry-failed`

Add or compute source operational fields:
- `run_status`
- `last_run_started_at`
- `last_run_finished_at`
- `last_error_at`
- `last_error_message`
- `active_job_count`

## UX Requirements
- Keep action labels operator-friendly and consistent.
- Distinguish clearly between Pause and Stop.
- Use disabled button states when an action is invalid for the current source status.
- Show immediate success/error feedback after actions.

## Acceptance Criteria
- Operators can start, pause, resume, stop, and retry failed work from the Sources page.
- Source detail displays live operational status and latest errors.
- Dashboard shows at least:
  - active sources
  - running jobs
  - paused jobs
  - failed jobs
- Backend source control endpoints behave consistently and safely.

## Notes
Pause should stop new work from being enqueued and ideally let active work finish unless hard-stop behavior is explicitly requested.
