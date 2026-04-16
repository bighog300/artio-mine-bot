# Job Runtime Visibility — Backend Spec

## Summary

Add persistent progress fields to `Job`, add a `JobEvent` table, instrument worker pipelines, and expose new API endpoints for live operator visibility.

## Existing backend files to change

- `app/db/models.py`
- `app/db/crud.py`
- `app/db/migrations/versions/` (new migration)
- `app/api/routes/operations.py`
- `app/api/routes/logs.py` (optional stream extension)
- `app/pipeline/runner.py`
- `app/pipeline/backfill_processor.py`

---

## 1. Data model changes

### 1.1 Extend `Job`
Add these nullable columns to the `Job` model:

- `current_stage: str | None`
- `current_item: str | None`
- `progress_current: int`
- `progress_total: int`
- `last_heartbeat_at: datetime | None`
- `last_log_message: str | None`
- `metrics_json: str | None`

Recommended SQLAlchemy shape:

```python
current_stage: Mapped[str | None] = mapped_column(String, nullable=True)
current_item: Mapped[str | None] = mapped_column(Text, nullable=True)
progress_current: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
progress_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
last_heartbeat_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
last_log_message: Mapped[str | None] = mapped_column(Text, nullable=True)
metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Notes:
- `current_item` should be `Text`, not `String`, because URLs and identifiers can be long.
- `metrics_json` should remain JSON-as-text for consistency with the current codebase.
- default `0` for progress values keeps old jobs readable.

### 1.2 Add `JobEvent`
Create a new model:

```python
class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, default="public")
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String, ForeignKey("sources.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTC_DATETIME, default=_now, nullable=False)
    level: Mapped[str] = mapped_column(String, default="info", nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Recommended indexes:
- `Index("ix_job_events_job_id_timestamp", "job_id", "timestamp")`
- `Index("ix_job_events_source_id_timestamp", "source_id", "timestamp")`
- `Index("ix_job_events_event_type", "event_type")`

This is append-only runtime history for operators.

---

## 2. Migration

Create a new Alembic migration that:
1. adds the new `jobs` columns
2. creates the `job_events` table
3. adds indexes

Keep downgrade support.

---

## 3. CRUD additions

Add helpers in `app/db/crud.py`.

### 3.1 `update_job_progress`
```python
async def update_job_progress(
    db: AsyncSession,
    job_id: str,
    *,
    stage: str | None = None,
    item: str | None = None,
    progress_current: int | None = None,
    progress_total: int | None = None,
    last_log_message: str | None = None,
    metrics: dict[str, Any] | None = None,
    heartbeat: bool = True,
) -> Job | None:
    ...
```

Behavior:
- fetch job
- update provided fields only
- set `last_heartbeat_at = now()` when `heartbeat=True`
- encode `metrics` to JSON string
- commit and refresh
- return updated job

### 3.2 `append_job_event`
```python
async def append_job_event(
    db: AsyncSession,
    *,
    job_id: str,
    source_id: str | None,
    event_type: str,
    message: str,
    level: str = "info",
    stage: str | None = None,
    context: dict[str, Any] | None = None,
) -> JobEvent:
    ...
```

Behavior:
- create event row
- JSON encode `context`
- commit/flush depending on existing project style
- return the event

### 3.3 `list_job_events`
```python
async def list_job_events(
    db: AsyncSession,
    job_id: str,
    *,
    limit: int = 100,
    before: datetime | None = None,
) -> list[JobEvent]:
    ...
```

Sort newest first in storage query; reverse in API response if needed.

### 3.4 Optional `get_job_detail`
Could simply reuse `get_job`, but a helper that eagerly includes related source may reduce route duplication.

---

## 4. API changes

### 4.1 Extend `GET /jobs`
In `app/api/routes/operations.py`, include these new fields in each job item:

- `current_stage`
- `current_item`
- `progress_current`
- `progress_total`
- `progress_percent`
- `last_heartbeat_at`
- `last_log_message`
- `metrics`

Recommended `progress_percent` logic:
```python
progress_percent = None
if job.progress_total and job.progress_total > 0:
    progress_percent = int((job.progress_current / job.progress_total) * 100)
```

Decode `metrics_json` using the existing `_parse_json`.

### 4.2 Add `GET /jobs/{job_id}`
Return:
- all list-job fields
- source/source name
- payload/result parsed JSON
- `is_stale` flag if:
  - status is `running`, and
  - `last_heartbeat_at` older than 2 minutes

### 4.3 Add `GET /jobs/{job_id}/events`
Response shape:
```json
{
  "items": [
    {
      "id": "...",
      "timestamp": "...",
      "level": "info",
      "event_type": "stage_changed",
      "stage": "crawling",
      "message": "Started crawl stage",
      "context": {"url": "..."}
    }
  ],
  "total": 42
}
```

### 4.4 Optional `GET /jobs/active`
Convenience endpoint for dashboard/queues:
- all non-terminal jobs
- maybe include stale flag

---

## 5. Live stream strategy

### Option A — recommended for first pass
Reuse `/logs/stream` and publish structured events with a discriminant:
```json
{
  "stream_type": "job_progress",
  "job_id": "...",
  "source_id": "...",
  "stage": "extracting",
  "message": "Extracted page",
  "progress_current": 12,
  "progress_total": 40,
  "timestamp": "..."
}
```

### Option B
Create `/jobs/stream` dedicated SSE endpoint later.

For this repo, Option A is lower-risk because SSE plumbing already exists in `logs.py`.

---

## 6. Worker instrumentation

### 6.1 `app/pipeline/runner.py`
Add progress updates around major stages of `run_full_pipeline`:
- `mapping`
- `crawling`
- `extracting`
- `writing` (when relevant)
- `completed`
- `failed`

Examples:
- before site map: `stage="mapping", item=source.url`
- before crawl: `stage="crawling"`
- during crawl: set current page URL as `current_item`
- before extraction: `stage="extracting"`
- during extraction: update page count processed
- on completion: final event + set final heartbeat

### 6.2 `app/pipeline/backfill_processor.py`
Instrument these steps:
- campaign job started
- fetching page
- cache hit / fetch
- extracting missing fields
- merging data into record
- updating campaign stats
- completed / failed

Backfill jobs are exactly the jobs operators will want to inspect live.

### 6.3 Helper function
Create a small helper function to keep instrumentation consistent:

```python
async def report_job_progress(
    db: AsyncSession,
    job_id: str,
    *,
    source_id: str | None = None,
    stage: str | None = None,
    item: str | None = None,
    message: str | None = None,
    progress_current: int | None = None,
    progress_total: int | None = None,
    metrics: dict[str, Any] | None = None,
    event_type: str = "progress",
    level: str = "info",
) -> None:
    ...
```

It should:
1. call `update_job_progress`
2. append a `JobEvent`
3. optionally emit to stream manager

This is the main implementation simplifier.

---

## 7. Event taxonomy

Use a small stable event vocabulary.

Recommended `event_type` values:
- `job_started`
- `job_heartbeat`
- `stage_changed`
- `item_started`
- `item_completed`
- `item_failed`
- `progress`
- `retry_scheduled`
- `job_completed`
- `job_failed`
- `job_cancelled`

Recommended stages:
- `starting`
- `mapping`
- `crawling`
- `extracting`
- `writing`
- `backfill_fetch`
- `backfill_extract`
- `backfill_merge`
- `finalizing`

---

## 8. Acceptance criteria

- `GET /jobs` returns progress fields for active jobs.
- Running jobs update `last_heartbeat_at`.
- Operators can retrieve `GET /jobs/{id}/events`.
- `runner.py` emits progress at stage boundaries.
- `backfill_processor.py` emits progress per record/page unit of work.
- A running job becomes visually stale if heartbeat stops.
- Existing job actions (`retry`, `pause`, `resume`, `cancel`) continue to work.

---

## 9. Implementation notes

- Keep backward compatibility with existing `Job` rows by using nullable fields + zero defaults.
- Avoid writing a `JobEvent` for every extremely chatty low-level loop if it will flood storage; prefer:
  - stage changes
  - item start/fail/complete
  - progress updates every N items or significant changes
- Keep `context` lightweight and JSON serializable.
