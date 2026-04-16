# Backend Spec

## Data Model Changes
- Ensure JobEvent includes source_id
- Extend Job with source_id (if not already present)

## New Endpoints
- GET /sources/{id}/operations
- GET /sources/{id}/runs
- GET /sources/{id}/events
- POST /sources/{id}/run
- POST /sources/{id}/pause
- POST /sources/{id}/resume
- POST /sources/{id}/cancel-active
- POST /sources/{id}/backfill

## Moderation
- POST /sources/{id}/moderated-actions/{action_id}/approve
- POST /sources/{id}/moderated-actions/{action_id}/reject

## SSE
- Extend stream filtering to support:
  - source_id
  - job_id
  - worker_id
  - stage
  - event_type
