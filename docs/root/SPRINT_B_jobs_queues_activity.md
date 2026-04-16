# Sprint B: Jobs, Queues, Activity, and Error Visibility

## Objective
Give operators visibility into what the crawler and extractor are doing by adding a jobs console, queue views, and clearer activity/error feedback.

## Scope

### Frontend
Add:
- `frontend/src/pages/Jobs.tsx`
- `frontend/src/pages/Queues.tsx`

Update:
- `frontend/src/pages/AuditTrail.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/shared/Layout.tsx`
- `frontend/src/lib/api.ts`

Jobs page should show:
- job id
- source
- type
- mode
- status
- started at
- duration
- pages processed
- records written
- failures
- current URL or current step if available

Queue page should show:
- queue name
- pending count
- running count
- failed count
- paused count
- oldest item age
- average wait time

Activity/error visibility:
- recent failures
- recent retries
- recent reruns
- latest source/job error
- links to source detail and job detail where possible

### Backend
Update:
- `app/api/routes/operations.py`
- `app/api/routes/logs.py`
- `app/api/routes/metrics.py`
- `app/api/schemas.py`
- `app/db/crud.py`

Add or confirm endpoints:
- `GET /api/jobs`
- `POST /api/jobs/{id}/retry`
- `POST /api/jobs/{id}/cancel`
- `POST /api/jobs/{id}/pause`
- `POST /api/jobs/{id}/resume`
- `GET /api/queues`
- `POST /api/queues/{name}/pause`
- `POST /api/queues/{name}/resume`
- `GET /api/logs/activity`

## UX Requirements
- Surface the latest error message without making operators dig through logs first.
- Keep queue and job statuses aligned with source status labels.
- Make failed jobs easy to retry from one click.
- Show empty states clearly.

## Acceptance Criteria
- Operators can view active and historical jobs.
- Operators can see queue backlog and bottlenecks.
- Activity logs are useful for debugging run failures.
- Dashboard exposes operational counts and recent failures.
- Job and queue actions are functional and safe.

## Notes
If queue storage is not first-class yet, derive queue views from jobs and statuses as an interim implementation.
