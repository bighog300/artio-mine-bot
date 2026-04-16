# Backend Spec

## Models
- Extend Job with:
  worker_id, current_stage, current_item, progress_current, progress_total,
  last_heartbeat_at, last_log_message, metrics_json

- Add WorkerState table:
  worker_id, status, current_job_id, current_stage, heartbeat_at

- JobEvent:
  job_id, worker_id, event_type, stage, message, context_json

## APIs
- GET /jobs
- GET /jobs/{id}
- GET /jobs/{id}/events
- POST /jobs/{id}/pause|resume|cancel|retry
- GET /workers

## Logic
- Enforce MAX_CONCURRENT_JOBS = 5
- Cooperative control checks in pipeline loops
- Emit structured SSE events
