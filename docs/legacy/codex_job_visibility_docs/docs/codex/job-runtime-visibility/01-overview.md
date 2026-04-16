# Job Runtime Visibility — Overview

## Goal

Enable an admin/operator to actively visualize what jobs are doing **while they are running**, not just whether they are queued/running/completed.

This repo already has:
- `frontend/src/pages/Jobs.tsx`
- `frontend/src/pages/Queues.tsx`
- `frontend/src/pages/Logs.tsx`
- `app/api/routes/operations.py`
- `app/api/routes/logs.py`
- `app/pipeline/runner.py`
- `app/pipeline/backfill_processor.py`

The current system provides:
- job list snapshots via `GET /jobs`
- queue snapshots via `GET /queues`
- generic activity/log views via `GET /logs`, `GET /logs/activity`, and SSE at `GET /logs/stream`

What is missing is **structured in-progress execution visibility**:
- current stage
- current item being processed
- heartbeat
- progress counters
- structured timeline of job events
- job detail view with live updates

## Desired operator experience

### Jobs page
Operators should see, at a glance:
- job status
- current stage
- current item / URL / record / page being processed
- progress (`current/total`)
- live heartbeat / stale indicator
- duration
- processed/failure counters
- quick link to a detail view

### Job detail
Operators should be able to open a single job and see:
- summary/header
- live progress bar
- current stage + current item
- event timeline
- recent structured logs
- counters/metrics
- retry / pause / resume / cancel actions

### Queues page
Operators should see:
- queue depth
- running count
- failure count
- oldest pending age
- active workers (derived or estimated)
- stuck jobs
- runtime throughput trends (phase 2)

## Constraints from current codebase

### Current backend
`app/api/routes/operations.py` returns job snapshots with:
- `id`
- `source_id`
- `source`
- `job_type`
- `status`
- `attempts`
- `max_attempts`
- `payload`
- `error_message`
- `processed_count`
- `failure_count`
- `duration_seconds`
- timestamps

This is a good base, but it lacks live execution fields.

### Current logging
`app/api/routes/logs.py` already exposes:
- log list
- filtered activity feed
- SSE log stream

This should be reused for live updates, but with **structured job progress events**.

### Current worker/pipeline
`app/pipeline/runner.py` and `app/pipeline/backfill_processor.py` log major events, but they do not persist in-progress step state in the database.

## Delivery approach

Implement in three phases.

### Phase 1 — high value, low risk
Add live progress fields to `Job` and show them in the Jobs page:
- `current_stage`
- `current_item`
- `progress_current`
- `progress_total`
- `last_heartbeat_at`
- `last_log_message`
- `metrics_json`

### Phase 2 — detailed visibility
Add `JobEvent` storage and API endpoints:
- `GET /jobs/{id}`
- `GET /jobs/{id}/events`

Build a Job detail page/drawer.

### Phase 3 — live UX
Push structured job updates over SSE and use them to refresh the jobs list/detail views with low latency.

## Non-goals for this implementation
- Full tracing / OpenTelemetry rollout
- Cross-service distributed tracing
- Websocket infrastructure
- Historical BI dashboarding beyond lightweight queue/runtime metrics
