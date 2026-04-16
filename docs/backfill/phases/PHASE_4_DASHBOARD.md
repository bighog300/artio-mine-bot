# Phase 4: Frontend Dashboard & UI

## Overview

Phase 4 is implemented as a **single-page dashboard architecture** centered on `frontend/src/pages/Backfill.tsx`. The page provides campaign/schedule visibility and schedule creation from one route.

**Status**: ✅ IMPLEMENTED (single-page approach)

**Prerequisites**: Phases 1, 2, & 3

---

## Implementation Approach

Instead of a component-library tree under `frontend/src/components/backfill/`, the implementation uses:

```text
frontend/src/
├── pages/
│   └── Backfill.tsx
├── api/
│   └── backfill.ts
├── lib/
│   └── api.ts
└── App.tsx
```

### Architecture decision (as implemented)

- Keep all backfill UI workflow in one page component
- Use TanStack Query for API reads/mutations
- Use file-local presentational helpers for tables/cards
- Reuse centralized API module for HTTP behavior and error normalization

---

## Backfill Page Component

**Location**: `frontend/src/pages/Backfill.tsx`

### Features Implemented

- Dashboard heading and explanatory copy
- Three KPI cards:
  - Total campaigns
  - Running campaigns
  - Total schedules
- Create schedule form:
  - name
  - cron expression
  - limit
  - default recurring schedule payload with filters/options
- Campaign listing table (name, status, progress, timestamp)
- Schedule listing table (name, cron, next run, enabled)
- Loading states for campaigns and schedules
- Error display for create-schedule mutation failures

### State Management

- Local component state via `useState`:
  - `name`
  - `cron`
  - `limit`
- Remote state via `useQuery`:
  - `queryKey: ["backfill-campaigns"]`
  - `queryKey: ["backfill-schedules"]`
- Mutations via `useMutation`:
  - `createBackfillSchedule`
  - Invalidates `backfill-schedules` on success

### Internal Helper Components (same file)

- `StatCard`
- `CampaignTable`
- `ScheduleTable`

### Styling

- Tailwind utility classes directly in JSX
- No backfill-specific CSS module or standalone stylesheet

---

## API Client

**Primary usage in page**: imports from `@/lib/api`

**Backfill adapter file**: `frontend/src/api/backfill.ts`

### Available API functions (actual)

From `frontend/src/lib/api.ts`:

- `getBackfillCampaigns()` → `GET /backfill/campaigns`
- `getBackfillSchedules()` → `GET /backfill/schedules`
- `createBackfillSchedule(input)` → `POST /backfill/schedules`

From `frontend/src/api/backfill.ts` (`backfillApi` object):

- `backfillApi.getCampaigns`
- `backfillApi.getSchedules`
- `backfillApi.createSchedule`

### Types in use

- `BackfillCampaign`
- `BackfillSchedule`
- `CreateBackfillScheduleInput`

### Error Handling

- Axios interceptor in `frontend/src/lib/api.ts` maps `response.data.detail` to `Error(detail)` when present
- Component displays create mutation error message inline in the schedule form section

---

## Routing and Navigation

### Route Configuration

**Location**: `frontend/src/App.tsx`

```tsx
<Route path="/backfill" element={<Backfill />} />
```

### Navigation

**Location**: `frontend/src/components/shared/Layout.tsx`

Sidebar contains:

```ts
{ to: "/backfill", label: "Backfill", icon: RefreshCw }
```

### Route Guards

- No route-level guard is defined in `App.tsx` for `/backfill`

---

## Integration Steps (Completed)

1. ✅ Implemented `frontend/src/pages/Backfill.tsx` as a complete page
2. ✅ Implemented/reused backfill API calls in `frontend/src/lib/api.ts`
3. ✅ Added adapter in `frontend/src/api/backfill.ts`
4. ✅ Added route `/backfill` in `frontend/src/App.tsx`
5. ✅ Added sidebar navigation item in shared layout

### Run and access

```bash
docker compose up frontend
# open http://localhost:5173/backfill
```

---

## Example UI (Actual)

### Dashboard view includes

1. Header section: title + short description
2. KPI card row with campaign/schedule counts
3. Create Schedule form
4. Recent Campaigns table
5. Schedules table

### Simplified structure snippet

```tsx
export function Backfill() {
  const [name, setName] = useState("Weekly Artist Refresh");
  const { data: campaigns } = useQuery({ queryKey: ["backfill-campaigns"], queryFn: getBackfillCampaigns });
  const { data: schedules } = useQuery({ queryKey: ["backfill-schedules"], queryFn: getBackfillSchedules });

  return (
    <div className="space-y-6">
      {/* stats, create form, campaigns table, schedules table */}
    </div>
  );
}
```

---

## Developer Guide

### Where to change behavior

- UI/layout/state: `frontend/src/pages/Backfill.tsx`
- Backfill API mapping: `frontend/src/api/backfill.ts`
- Raw endpoint functions/types: `frontend/src/lib/api.ts`
- Route registration: `frontend/src/App.tsx`
- Navigation entry: `frontend/src/components/shared/Layout.tsx`

### Adding a new backfill action

1. Add endpoint function/type to `frontend/src/lib/api.ts`
2. Optionally re-export/map via `frontend/src/api/backfill.ts`
3. Add query/mutation usage in `Backfill.tsx`
4. Add UI controls + loading/error states

---

## Verification

Phase 4 is considered complete for current architecture when:

- ✅ `/backfill` route resolves and renders
- ✅ Campaign and schedule data queries execute
- ✅ Schedule creation submits to backend
- ✅ Form mutation errors surface in UI
- ✅ Navigation link to backfill exists in sidebar

Suggested checks:

```bash
# frontend route config
rg -n 'path="/backfill"|Backfill' frontend/src/App.tsx

# nav entry
rg -n '"/backfill"|Backfill' frontend/src/components/shared/Layout.tsx

# page implementation
rg -n 'useQuery|useMutation|Create Schedule|Recent Campaigns|Schedules' frontend/src/pages/Backfill.tsx
```

---

## Appendix: Architecture Notes

### Original documented design (not implemented)

Historical docs described a component-library split (e.g., `CampaignList`, `LiveMonitor`, etc.). That structure is not present in this codebase.

### Current implemented design

A single consolidated page (`Backfill.tsx`) with local helper components and TanStack Query.

### When to consider refactoring

Refactor into `frontend/src/components/backfill/` if:

- Backfill page becomes too large/complex
- Component reuse is needed across routes
- Multiple developers need clear ownership boundaries per UI module

