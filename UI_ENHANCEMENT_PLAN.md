# Artio Miner — Web UI Enhancement Plan

## Overview

Six enhancements in implementation order. Each section includes:
- Exact files to create or modify
- Backend changes needed (if any)
- Frontend implementation notes
- What to test

Work is ordered so each change is independently deployable and does not
break any prior fix from the handoff doc.

---

## Enhancement 1 — Live pipeline progress panel

**Effort:** Medium | **Risk:** Low | **Impact:** High

### What it is
Replace the single progress bar on `SourceDetail` with a 4-stat row
(pages found / crawled / extracted / records), a pipeline stage checklist
showing which step is active, and a live record-type breakdown bar.
Everything updates on the existing 3-second polling interval.

### Backend changes

**File: `app/api/schemas.py`**

Extend `MineStatusProgress` with the missing counts:

```python
class MineStatusProgress(BaseModel):
    pages_crawled: int
    pages_total_estimated: int
    pages_eligible_for_extraction: int   # ADD
    pages_classified: int                # ADD
    pages_skipped: int                   # ADD
    pages_error: int                     # ADD
    records_extracted: int
    records_by_type: dict[str, int]      # ADD
    images_collected: int                # ADD
    percent_complete: int
```

**File: `app/api/routes/mine.py`** — `get_mining_status` handler

Add these queries after the existing `pages_crawled` line:

```python
pages_eligible = await crud.count_pages_in_statuses(
    db, source_id=source_id, statuses=["fetched", "classified"]
)
pages_classified = await crud.count_pages(db, source_id=source_id, status="classified")
pages_skipped = await crud.count_pages(db, source_id=source_id, status="skipped")
pages_error = await crud.count_pages(db, source_id=source_id, status="error")

# Records by type
records_by_type: dict[str, int] = {}
for rtype in ("artist", "event", "exhibition", "venue", "artwork"):
    records_by_type[rtype] = await crud.count_records(
        db, source_id=source_id, record_type=rtype
    )

# Images collected
from sqlalchemy import func, select
from app.db.models import Image
images_count = (
    await db.execute(
        select(func.count(Image.id)).where(Image.source_id == source_id)
    )
).scalar_one()
```

Note: `crud.count_records` already accepts `source_id` but not
`record_type` — add that optional parameter:

**File: `app/db/crud.py`** — `count_records`

```python
async def count_records(
    db: AsyncSession,
    source_id: str | None = None,
    status: str | None = None,
    record_type: str | None = None,   # ADD
) -> int:
    q = select(func.count(Record.id))
    if source_id:
        q = q.where(Record.source_id == source_id)
    if status:
        q = q.where(Record.status == status)
    if record_type:                    # ADD
        q = q.where(Record.record_type == record_type)
    return (await db.execute(q)).scalar_one()
```

### Frontend changes

**File: `frontend/src/lib/api.ts`**

Update `MiningStatus.progress` interface to match the new schema fields.

**File: `frontend/src/pages/SourceDetail.tsx`**

Replace the existing progress section in the `overview` tab with:

1. A `<PipelineStats>` component — four `StatCard` elements showing pages
   found, crawled (with mini bar), extracted (with mini bar), records (with
   `↑ N in last minute` delta if polling detects change).
2. A `<PipelineStages>` component — vertical checklist:
   - Site mapping (done/active/pending dot)
   - Crawling — `N / M pages`
   - Extracting — `N pages processed`
   - Image collection
   Derive current stage from `source.status` field.
3. A `<RecordTypeBar>` component — proportional coloured bar, one segment
   per type with a label below. Hide if all zeroes.

Keep the site map section and the existing job display below these.

**New file: `frontend/src/components/pipeline/PipelineProgress.tsx`**

Extract all three sub-components here so `SourceDetail` stays readable.

### What to test
- Progress values update every 3 seconds during an active crawl.
- Stage checklist correctly shows `done` for mapping and `active` for
  crawling when status is `"crawling"`.
- Record type bar renders proportionally and handles missing types.
- No change to any existing mining control buttons.

---

## Enhancement 2 — Bulk review queue (records page)

**Effort:** Medium | **Risk:** Low | **Impact:** High

### What it is
Replace the 3-column card grid on `Records` with a compact table view.
Add status tabs (Pending / Approved / Rejected) replacing the status
dropdown. Add row-level approve/reject/edit actions. Add checkbox
multi-select for batch approve/reject. Show confidence signal reasons as
inline subtext under the record title.

### Backend changes

None. The existing list, approve, reject, and bulk-approve endpoints are
sufficient. The `confidence_reasons` field is already returned in
`RecordListItem`.

### Frontend changes

**File: `frontend/src/pages/Records.tsx`**

1. Replace the `status` dropdown with three tab buttons:
   `Pending (N) / Approved (N) / Rejected (N)`. Each tab sets
   `status` filter and shows a live count from the paginated `total` field.

2. Replace the card grid with a table. Columns:
   - Checkbox (multi-select)
   - Record (title + confidence reasons as 11px subtext)
   - Type badge
   - Confidence badge (score number + band colour)
   - Source name (truncated)
   - Actions (✓ approve, ✕ reject, Edit link)

3. Add a `selectedIds: Set<string>` state. Show a `Bulk actions` bar
   above the table when `selectedIds.size > 0` with:
   - "Approve selected (N)" button → calls `approveRecord` for each in
     the set (can parallelise with `Promise.all`).
   - "Reject selected (N)" button.
   - "Clear selection" link.

4. Keep the existing "Approve all HIGH confidence" button in the top-right.

5. Keep all existing filters (source, type, confidence band, search).
   Remove the now-redundant status dropdown (replaced by tabs).

6. Add simple pagination — prev/next controls using `skip`/`limit`.
   Default `limit=25`.

**New file: `frontend/src/components/records/RecordTableRow.tsx`**

Stateless row component accepting a record and callback props, so the
parent table is not bloated.

### What to test
- Tab counts update after approve/reject actions (invalidate `["records"]`
  query and also re-fetch counts by re-querying each status).
- Multi-select checkbox: header checkbox selects/deselects all visible rows.
- Bulk approve calls are made concurrently, not sequentially.
- Existing navigation to `/records/:id` edit page still works from the
  Edit action.

---

## Enhancement 3 — Inline quick-edit on record detail

**Effort:** Medium | **Risk:** Low | **Impact:** High

### What it is
The `RecordDetail` page currently requires a full page load to edit and
save. Enhance it to:
- Show all fields as editable in-place when "Edit" is clicked (already
  partially done — the scaffold exists).
- Add the image selection panel (see Enhancement 4) directly below the
  field editor.
- Show confidence signal reasons as a readable sentence at the bottom.
- Add keyboard shortcut: `a` to approve, `r` to reject when not in an
  input.
- Add prev/next navigation buttons to step through records without going
  back to the list.

### Backend changes

**File: `app/api/routes/records.py`** — add adjacent-record endpoint

```python
@router.get("/{record_id}/adjacent")
async def get_adjacent_records(
    record_id: str,
    source_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return the prev and next record IDs for navigation."""
    records = await crud.list_records(
        db, source_id=source_id, status=status, limit=10000
    )
    ids = [r.id for r in records]
    try:
        idx = ids.index(record_id)
    except ValueError:
        return {"prev_id": None, "next_id": None}
    return {
        "prev_id": ids[idx - 1] if idx > 0 else None,
        "next_id": ids[idx + 1] if idx < len(ids) - 1 else None,
    }
```

This is a pragmatic first version — a cursor-based approach would be
better at scale but this is sufficient for typical source sizes (<500
records).

### Frontend changes

**File: `frontend/src/pages/RecordDetail.tsx`**

1. Add `useEffect` for keyboard shortcuts — `keydown` listener on
   `document` that fires `approveMutation` on `a` and `rejectMutation`
   on `r`, skipped when `event.target` is an input/textarea.

2. Add `useQuery` for `/records/:id/adjacent?source_id=...&status=pending`
   and render prev/next arrow buttons in the header bar.

3. Move the field edit section to always-visible inline form inputs
   (remove the "Edit / Save" toggle — it's confusing). Show a "Save
   changes" button that appears only when `formData !== record` (dirty
   state). Auto-save on blur is an option but risky; explicit save button
   is safer.

4. Render `confidence_reasons` as: `"Confidence signals: name present ·
   bio present · 3 images found"` below the confidence bar.

5. Add the `ImageSelectionPanel` component (see Enhancement 4) below
   the fields section.

**File: `frontend/src/lib/api.ts`**

Add:
```typescript
export const getAdjacentRecords = (
  id: string,
  params?: { source_id?: string; status?: string }
): Promise<{ prev_id: string | null; next_id: string | null }> =>
  api.get(`/records/${id}/adjacent`, { params }).then((r) => r.data);
```

### What to test
- `a` key approves the current record and navigates to the next one.
- `r` key does not fire when the user is typing in the bio textarea.
- Dirty state detection: save button appears after any field change.
- Prev/next navigation preserves the filter context (status=pending).

---

## Enhancement 4 — Image selection panel

**Effort:** Low-Medium | **Risk:** Low | **Impact:** Medium

### What it is
Replace the plain URL list in record detail with a thumbnail grid.
Images validated with `is_valid=true` are shown normally. Low-confidence
or unvalidated images are greyed. Clicking a thumbnail sets it as primary.
The primary image shows a checkmark overlay.

### Backend changes

None. The `/records/:id/images` endpoint and `setPrimaryImage` call are
already implemented. The `is_valid` and `confidence` fields are already
on `ImageRecord`.

### Frontend changes

**New file: `frontend/src/components/records/ImageSelectionPanel.tsx`**

Props:
```typescript
interface Props {
  recordId: string;
  primaryImageId: string | null;
  onPrimarySet: (imageId: string) => void;
}
```

Implementation:
1. `useQuery` for `/images?record_id=recordId` — already available.
2. Render a `grid-cols-4 gap-2` thumbnail grid.
3. Each cell: `<img src={url} />` with `object-fit: cover`, 80×80px,
   `rounded-md`. Add `opacity-40` class if `!image.is_valid`.
4. Primary image: add a blue checkmark overlay (absolute positioned
   small circle with checkmark SVG).
5. On click: call `setPrimaryImage(recordId, imageId)`.
6. Below the grid: `N images · M valid` summary line.
7. If no images: render `"No images collected for this record."` with a
   muted style.

**File: `frontend/src/pages/RecordDetail.tsx`**

Import and render `<ImageSelectionPanel>` below the field editor, passing
`record.id`, `record.primary_image_id`, and an `onPrimarySet` callback
that calls the mutation and invalidates the record query.

### What to test
- Primary image checkmark appears on the correct thumbnail after clicking.
- Opacity changes correctly for invalid images.
- Zero-image state renders gracefully.
- Changing primary image updates the card thumbnail on the Records list
  (check that the list query is invalidated).

---

## Enhancement 5 — Activity feed on dashboard

**Effort:** Low | **Risk:** Low | **Impact:** Medium

### What it is
Add a "Recent activity" section to the Dashboard showing the last 20
meaningful events — records created, pipeline completions, errors — as a
time-ordered list. Replaces the currently static "Recent sources" table
with a two-column layout: stats on the left, activity on the right.

### Backend changes

**File: `app/api/routes/logs.py`** — add activity summary endpoint

```python
@router.get("/activity")
async def get_activity(
    limit: int = Query(default=20, ge=1, le=100),
    source_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return recent meaningful log events for the activity feed."""
    ACTIVITY_EVENTS = [
        "record_created",
        "pipeline_complete",
        "pipeline_error",
        "crawl_stage_error",
        "extraction_started",
        "pages_processed",
    ]
    items, _ = await list_logs(
        db,
        search=None,
        source_id=source_id,
        limit=limit,
        skip=0,
        # Filter to meaningful events only
        # list_logs already supports search — use message filter instead
    )
    # Filter client-side to activity events (pragmatic for small limit)
    activity = [
        i for i in items
        if any(evt in i["message"] for evt in ACTIVITY_EVENTS)
    ]
    return {"items": activity[:limit]}
```

Alternatively, if `list_logs` supports a message search param, pass a
pipe-separated pattern. The endpoint is simple enough that filtering
post-query on a 100-row result is fine.

**File: `frontend/src/lib/api.ts`**

```typescript
export const getActivityFeed = (params?: {
  source_id?: string;
  limit?: number;
}): Promise<{ items: LogEntry[] }> =>
  api.get("/logs/activity", { params }).then((r) => r.data);
```

### Frontend changes

**File: `frontend/src/pages/Dashboard.tsx`**

1. Replace the single-column layout with a two-column grid at the bottom
   (stats/sources on the left, activity feed on the right).

2. Add a `useQuery` for `getActivityFeed({ limit: 20 })` with a
   `refetchInterval: 10000`.

3. Render the activity feed as a compact list:
   - Icon/colour dot indicating level (green for info, amber for warning,
     red for error).
   - Event message (cleaned up — strip log key prefix, capitalise first
     letter).
   - Relative timestamp (`2 min ago`).
   - If `source_id` is set, link to `/sources/:id`.

4. Keep the 4-stat card row at the top unchanged.

5. The existing "Recent sources" table can remain as a third section below,
   or be compressed to 3 rows.

### What to test
- Activity feed refreshes every 10 seconds.
- Error events appear in red.
- Feed is empty when no sources have been mined.
- Relative timestamps update on each refresh.

---

## Enhancement 6 — Jobs tab, Pages nav fix, Add Source options

**Effort:** Low | **Risk:** Low | **Impact:** Low-Medium

Three small fixes bundled as one sprint.

### 6a — Jobs tab in SourceDetail

**File: `frontend/src/pages/SourceDetail.tsx`** — `jobs` tab content

Replace the placeholder with a real jobs table. Data is already available
via `crud.list_jobs`; need an API route.

**File: `app/api/routes/sources.py`** — add jobs sub-route

```python
@router.get("/{source_id}/jobs")
async def list_source_jobs(source_id: str, db: AsyncSession = Depends(get_db)):
    from app.db.crud import list_jobs
    jobs = await list_jobs(db, source_id=source_id)
    return {"items": [
        {
            "id": j.id,
            "job_type": j.job_type,
            "status": j.status,
            "attempts": j.attempts,
            "started_at": j.started_at,
            "completed_at": j.completed_at,
            "error_message": j.error_message,
        }
        for j in jobs
    ]}
```

**File: `frontend/src/lib/api.ts`**

```typescript
export const getSourceJobs = (sourceId: string) =>
  api.get(`/sources/${sourceId}/jobs`).then((r) => r.data);
```

**File: `frontend/src/pages/SourceDetail.tsx`** — jobs tab render

Table columns: Type | Status | Started | Duration | Error (if any).
Duration = `completed_at - started_at` formatted as `Xm Ys`.
Newest job at the top.

### 6b — Fix broken Pages nav link

**File: `frontend/src/components/shared/Layout.tsx`**

The nav item points to `/pages`, which has no route. The `Pages` component
exists at `frontend/src/pages/Pages.tsx`.

**File: `frontend/src/App.tsx`**

Add the missing route:
```tsx
import { Pages } from "@/pages/Pages";
// ...
<Route path="/pages" element={<Pages />} />
```

No other changes needed — `Pages.tsx` is already implemented.

### 6c — Add Source dialog: crawl depth and max pages

**File: `frontend/src/pages/Sources.tsx`** — `Add Source` dialog

Add two optional fields below the Name field:

```tsx
<details className="text-sm text-gray-500 cursor-pointer">
  <summary>Advanced options</summary>
  <div className="mt-2 space-y-2">
    <div>
      <label>Max pages (default: 500)</label>
      <input type="number" value={maxPages} onChange={...} />
    </div>
    <div>
      <label>Max depth (default: 3)</label>
      <input type="number" min="1" max="10" value={maxDepth} onChange={...} />
    </div>
  </div>
</details>
```

Pass them to `startMining(source.id, { max_pages: maxPages, max_depth: maxDepth })`.
The `MineOptions` type and backend handler already accept these params.

---

## Implementation order

| # | Enhancement | Backend changes | Frontend changes | Priority |
|---|-------------|----------------|-----------------|----------|
| 1 | Live pipeline progress | `schemas.py`, `mine.py`, `crud.py` | `SourceDetail.tsx`, new `PipelineProgress.tsx` | Start here |
| 2 | Bulk review queue | None | `Records.tsx`, new `RecordTableRow.tsx` | High |
| 3 | Inline quick-edit | `records.py` (adjacent endpoint) | `RecordDetail.tsx` | High |
| 4 | Image selection panel | None | new `ImageSelectionPanel.tsx`, `RecordDetail.tsx` | Medium |
| 5 | Activity feed | `logs.py` (activity endpoint) | `Dashboard.tsx` | Medium |
| 6 | Jobs tab + nav fix + advanced add | `sources.py` (jobs sub-route) | `Layout.tsx`, `App.tsx`, `Sources.tsx` | Low |

Enhancements 1–3 should be done first; they address the core operator
workflow (run pipeline → see progress → review records). 4–6 are
independently shippable at any point.

---

## Shared utilities to add

**File: `frontend/src/lib/utils.ts`**

Add these helpers used by multiple enhancements:

```typescript
// Format seconds into "Xm Ys"
export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// Delta between two ISO timestamps in seconds
export function diffSeconds(a: string, b: string): number {
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / 1000);
}

// Capitalise first letter, strip log key prefix (e.g. "record_created" → "Record created")
export function formatLogMessage(msg: string): string {
  return msg.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}
```

---

## Things not to change

Per the handoff doc — do not touch:

- Queue/enqueue flow (`app/queue.py`, `mine.py` enqueue logic)
- Timezone fix in models or migrations
- Worker service in `docker-compose.yml`
- HTML null-byte sanitisation in the crawler
- Stage-aware resume logic in `mine.py`
- App-level extraction dedupe in `runner.py`
- Any Alembic migration file
