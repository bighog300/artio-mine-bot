# Job Runtime Visibility — Frontend Spec

## Summary

Add live progress and drill-down visibility to the existing Jobs and Queues pages, and create a dedicated Job Detail experience.

## Existing frontend files to change

- `frontend/src/pages/Jobs.tsx`
- `frontend/src/pages/Queues.tsx`
- `frontend/src/pages/Logs.tsx` (optional stream reuse patterns)
- `frontend/src/lib/api.ts`
- `frontend/src/App.tsx` (if adding a detail route)
- optionally add:
  - `frontend/src/pages/JobDetail.tsx`
  - `frontend/src/components/jobs/JobProgressBar.tsx`
  - `frontend/src/components/jobs/JobEventTimeline.tsx`
  - `frontend/src/components/jobs/HeartbeatBadge.tsx`

---

## 1. API client changes

Add client functions in `frontend/src/lib/api.ts`:

```ts
export const getJob = (jobId: string): Promise<JobDetail> =>
  api.get(`/jobs/${jobId}`).then((r) => r.data);

export const getJobEvents = (
  jobId: string,
  params?: { limit?: number }
): Promise<{ items: JobEvent[]; total: number }> =>
  api.get(`/jobs/${jobId}/events`, { params }).then((r) => r.data);
```

Extend `Job` type to include:
- `current_stage?: string | null`
- `current_item?: string | null`
- `progress_current?: number`
- `progress_total?: number`
- `progress_percent?: number | null`
- `last_heartbeat_at?: string | null`
- `last_log_message?: string | null`
- `metrics?: Record<string, unknown>`
- `is_stale?: boolean`

Add `JobEvent` and `JobDetail` interfaces.

---

## 2. Jobs page

### Current state
`frontend/src/pages/Jobs.tsx` currently shows:
- source
- type
- status
- timing
- processed
- failures
- actions

### Change request
Update the table to show:
- source
- type
- status
- **stage**
- **current item**
- **progress bar**
- duration
- processed/failures
- heartbeat
- actions
- detail link/button

Suggested column set:
1. Source
2. Type
3. Status
4. Stage
5. Current item
6. Progress
7. Timing
8. Heartbeat
9. Actions

### UI details
- truncate `current_item` with tooltip/title
- show progress bar only if `progress_total > 0`
- show heartbeat badge:
  - green: healthy/running
  - amber: stale
  - gray: terminal/no heartbeat needed
- keep polling every 5 seconds initially
- phase 2: merge in SSE updates for active jobs

---

## 3. Job detail view

Implement either:
- a new page route `/jobs/:id`, or
- a slide-over drawer launched from the Jobs page

Recommended: **new page route**, because operators may want deep links.

### Layout
#### Header
- source name / source id
- job type
- status badge
- started/completed timestamps
- duration
- heartbeat badge
- action buttons

#### Summary cards
- current stage
- current item
- progress current/total
- processed count
- failure count

#### Live progress section
- progress bar
- latest log message
- metrics key-value chips/cards

#### Timeline section
Render `JobEvent` entries in chronological order:
- timestamp
- event_type badge
- stage badge
- message
- expandable JSON context

#### Related logs (optional)
Link out to Logs page filtered by `source_id` and maybe job identifier once available.

---

## 4. Queues page

### Current state
`frontend/src/pages/Queues.tsx` shows:
- pending
- running
- failed
- paused
- oldest item age

### Change request
Augment with:
- active workers (if available)
- stale jobs count
- avg runtime of running jobs (derived from jobs list if no dedicated endpoint)
- top active stages
- link to active jobs filtered by queue

For phase 1, it is acceptable to keep `GET /queues` as-is and derive extra cards from `GET /jobs`.

### Suggested additions
Under each queue card:
- `Stale jobs`
- `Longest running job`
- `Top current stage`

---

## 5. SSE integration

The repo already uses `EventSource` in `frontend/src/pages/Logs.tsx`.

Use the same pattern for live job updates:
- subscribe on Jobs page and Job detail page
- listen only while mounted
- apply updates optimistically to React Query cache for `["jobs"]` and `["job", id]`

If SSE payloads are not ready in phase 1, keep polling:
- Jobs page: `refetchInterval: 5000`
- Job detail: `refetchInterval: 3000` while active

---

## 6. UX edge cases

- For jobs without progress totals, show em dash instead of a broken progress bar.
- For terminal jobs, do not show stale warning.
- For paused jobs, show paused badge, not stale.
- For failed jobs, surface `error_message` near the top of the detail page.
- For long current items (URLs), clamp to one line with title hover.

---

## 7. Acceptance criteria

- Jobs page shows stage, current item, progress, heartbeat.
- Operators can open a job detail view.
- Job detail shows timeline entries from `/jobs/{id}/events`.
- Active jobs refresh automatically.
- Existing retry/pause/resume/cancel actions continue to work.
- No regressions to current Jobs or Queues navigation.

---

## 8. Recommended implementation order

1. Extend TS types and API client.
2. Update Jobs table with new columns.
3. Add `JobDetail.tsx`.
4. Add job event timeline component.
5. Add optional SSE cache patching.
6. Improve Queues page summaries using active job data.
