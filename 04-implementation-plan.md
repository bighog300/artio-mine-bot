# Codex Implementation Plan — Job Runtime Visibility

## Objective

Implement operator-facing runtime visibility for jobs in this repo.

Deliver:
1. backend persistence for live progress
2. job event timeline storage
3. API endpoints for job detail + events
4. frontend jobs list enhancements
5. job detail page
6. optional SSE wiring if practical within scope

---

## Work breakdown

### Step 1 — database/model layer
- Extend `Job` in `app/db/models.py`
- Add new `JobEvent` model
- Generate a migration in `app/db/migrations/versions/`

Definition of done:
- migrations apply cleanly
- existing app still starts

### Step 2 — CRUD layer
Add helpers in `app/db/crud.py`:
- `update_job_progress`
- `append_job_event`
- `list_job_events`

Definition of done:
- helpers are covered by unit tests if practical
- JSON serialization/deserialization is safe

### Step 3 — API layer
Change `app/api/routes/operations.py`:
- extend `GET /jobs`
- add `GET /jobs/{job_id}`
- add `GET /jobs/{job_id}/events`

Definition of done:
- endpoints return stable JSON
- terminal and running jobs both serialize correctly
- stale flag is correct for heartbeat timeout

### Step 4 — worker instrumentation
Instrument:
- `app/pipeline/runner.py`
- `app/pipeline/backfill_processor.py`

Add a common helper for reporting progress.

Definition of done:
- stage changes are persisted
- current item is visible for at least the main loops
- progress counters update during work
- job events are appended at meaningful milestones

### Step 5 — frontend API/types
Update `frontend/src/lib/api.ts`:
- new types/interfaces
- `getJob`
- `getJobEvents`

Definition of done:
- frontend builds without type errors

### Step 6 — Jobs page
Update `frontend/src/pages/Jobs.tsx`:
- stage column
- current item column
- progress bar
- heartbeat badge
- link/button to detail page

Definition of done:
- list is readable at desktop width
- actions still work

### Step 7 — Job detail
Add:
- `frontend/src/pages/JobDetail.tsx`
- route in `frontend/src/App.tsx`

Definition of done:
- shows summary, progress, events, error state
- auto-refreshes while active

### Step 8 — Queues improvements
Update `frontend/src/pages/Queues.tsx` to show a few derived runtime indicators.

Definition of done:
- queue view better reflects operator runtime health
- no need for a large charting effort in this pass

---

## Testing guidance

### Backend
Add or update tests for:
- `GET /jobs` shape
- `GET /jobs/{id}`
- `GET /jobs/{id}/events`
- stale heartbeat logic
- progress helper functions

### Frontend
At minimum:
- build passes
- routes render
- jobs page handles null progress fields
- job detail handles empty events

---

## Practical implementation notes

- Preserve existing status mapping behavior (`done` => `completed`) in routes.
- Avoid noisy event writes in tight loops; batch or sample if needed.
- Prefer small reusable UI components:
  - `JobProgressBar`
  - `HeartbeatBadge`
  - `JobEventTimeline`
- Keep styling consistent with the existing plain Tailwind UI.

---

## Nice-to-have, only if scope allows

- live SSE updates for jobs
- filters by stage / stale state
- deep links from source detail job rows into job detail page
- links from job detail into filtered logs
