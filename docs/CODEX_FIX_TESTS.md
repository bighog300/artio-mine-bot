# CODEX: Add Frontend Tests & Fix Backend Test Failure

## OBJECTIVE

1. Add comprehensive frontend tests for `Backfill.tsx` component
2. Fix the timezone-aware datetime bug in `app/api/routes/operations.py`

---

## TASK 1: FIX BACKEND TEST FAILURE (Priority: CRITICAL)

### Issue Analysis

**Test Failure:** `test_jobs_include_runtime_visibility_fields`

**Error:**
```python
TypeError: can't subtract offset-naive and offset-aware datetimes
```

**Location:** `app/api/routes/operations.py:48`

**Root Cause:**
```python
def _is_job_stale(job: Job) -> bool:
    if job.status != "running" or job.last_heartbeat_at is None:
        return False
    return (datetime.now(UTC) - job.last_heartbeat_at) > timedelta(minutes=2)
    #       ^^^^^^^^^^^^^^^^^^^^^ timezone-aware
    #                              ^^^^^^^^^^^^^^^^^^^^ timezone-naive (from DB)
```

The `datetime.now(UTC)` is timezone-aware, but `job.last_heartbeat_at` from the database is timezone-naive.

### Fix Required

**File:** `app/api/routes/operations.py`

**Current Code (Line ~48):**
```python
def _is_job_stale(job: Job) -> bool:
    if job.status != "running" or job.last_heartbeat_at is None:
        return False
    return (datetime.now(UTC) - job.last_heartbeat_at) > timedelta(minutes=2)
```

**Fixed Code:**
```python
def _is_job_stale(job: Job) -> bool:
    if job.status != "running" or job.last_heartbeat_at is None:
        return False
    
    # Ensure both datetimes are timezone-aware for comparison
    now = datetime.now(UTC)
    last_heartbeat = job.last_heartbeat_at
    
    # If last_heartbeat is naive, make it UTC-aware
    if last_heartbeat.tzinfo is None:
        last_heartbeat = last_heartbeat.replace(tzinfo=UTC)
    
    return (now - last_heartbeat) > timedelta(minutes=2)
```

### Implementation Script

```bash
#!/bin/bash
set -e

cd /home/runner/work/artio-mine-bot/artio-mine-bot

echo "=========================================="
echo "  FIXING BACKEND TEST FAILURE"
echo "=========================================="
echo ""

# Fix the timezone issue
cat > /tmp/operations_fix.py << 'PYFIX'
from datetime import UTC, datetime, timedelta

def _is_job_stale(job: Job) -> bool:
    if job.status != "running" or job.last_heartbeat_at is None:
        return False
    
    # Ensure both datetimes are timezone-aware for comparison
    now = datetime.now(UTC)
    last_heartbeat = job.last_heartbeat_at
    
    # If last_heartbeat is naive, make it UTC-aware
    if last_heartbeat.tzinfo is None:
        last_heartbeat = last_heartbeat.replace(tzinfo=UTC)
    
    return (now - last_heartbeat) > timedelta(minutes=2)
PYFIX

# Apply fix to operations.py
# Find and replace the _is_job_stale function
python3 << 'PYSCRIPT'
import re

with open('app/api/routes/operations.py', 'r') as f:
    content = f.read()

# Find and replace the function
old_function = r'def _is_job_stale\(job: Job\) -> bool:\s+if job\.status != "running" or job\.last_heartbeat_at is None:\s+return False\s+return \(datetime\.now\(UTC\) - job\.last_heartbeat_at\) > timedelta\(minutes=2\)'

new_function = '''def _is_job_stale(job: Job) -> bool:
    if job.status != "running" or job.last_heartbeat_at is None:
        return False
    
    # Ensure both datetimes are timezone-aware for comparison
    now = datetime.now(UTC)
    last_heartbeat = job.last_heartbeat_at
    
    # If last_heartbeat is naive, make it UTC-aware
    if last_heartbeat.tzinfo is None:
        last_heartbeat = last_heartbeat.replace(tzinfo=UTC)
    
    return (now - last_heartbeat) > timedelta(minutes=2)'''

content = re.sub(old_function, new_function, content, flags=re.MULTILINE | re.DOTALL)

with open('app/api/routes/operations.py', 'w') as f:
    f.write(content)

print("✅ Fixed timezone issue in operations.py")
PYSCRIPT

# Verify the fix
echo ""
echo "=== Verifying Fix ==="
grep -A15 "def _is_job_stale" app/api/routes/operations.py

# Run the failing test
echo ""
echo "=== Running Previously Failing Test ==="
pytest tests/test_operations_sprints.py::test_jobs_include_runtime_visibility_fields -vv

echo ""
echo "✅ Backend fix complete"
```

### Alternative: Simple One-Liner Fix

If the regex replacement is too complex, use this simpler approach:

```python
# In app/api/routes/operations.py, line ~48
# Change this:
return (datetime.now(UTC) - job.last_heartbeat_at) > timedelta(minutes=2)

# To this:
last_heartbeat = job.last_heartbeat_at.replace(tzinfo=UTC) if job.last_heartbeat_at.tzinfo is None else job.last_heartbeat_at
return (datetime.now(UTC) - last_heartbeat) > timedelta(minutes=2)
```

---

## TASK 2: ADD FRONTEND TESTS FOR BACKFILL.TSX

### Test File Structure

**Location:** `frontend/src/pages/__tests__/Backfill.test.tsx`

### Test Coverage Requirements

Based on the actual implementation, test:
1. ✅ Component renders without errors
2. ✅ Loading state displays correctly
3. ✅ Error handling works
4. ✅ KPI cards display data
5. ✅ Campaign table renders
6. ✅ Schedule table renders
7. ✅ Schedule creation form works
8. ✅ Schedule creation mutation succeeds
9. ✅ Schedule creation mutation fails gracefully

### Implementation

```bash
#!/bin/bash
set -e

cd /home/runner/work/artio-mine-bot/artio-mine-bot

echo "=========================================="
echo "  ADDING FRONTEND TESTS"
echo "=========================================="
echo ""

# Create test directory
mkdir -p frontend/src/pages/__tests__

# Create comprehensive test file
cat > frontend/src/pages/__tests__/Backfill.test.tsx << 'TSX'
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { Backfill } from '../Backfill';
import * as backfillApi from '@/api/backfill';

// Mock the API
vi.mock('@/api/backfill');

// Helper to wrap component with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
};

describe('Backfill Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('displays loading indicators while fetching data', () => {
      // Mock API calls that never resolve
      vi.mocked(backfillApi.getCampaigns).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );
      vi.mocked(backfillApi.getSchedules).mockImplementation(
        () => new Promise(() => {})
      );

      render(<Backfill />, { wrapper: createWrapper() });

      // Should show loading states
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('displays error message when campaigns fetch fails', async () => {
      vi.mocked(backfillApi.getCampaigns).mockRejectedValue(
        new Error('Failed to fetch campaigns')
      );
      vi.mocked(backfillApi.getSchedules).mockResolvedValue({
        items: [],
      });

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });
    });

    it('displays error message when schedules fetch fails', async () => {
      vi.mocked(backfillApi.getCampaigns).mockResolvedValue({
        items: [],
        total: 0,
      });
      vi.mocked(backfillApi.getSchedules).mockRejectedValue(
        new Error('Failed to fetch schedules')
      );

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });
    });
  });

  describe('KPI Cards', () => {
    it('displays campaign statistics', async () => {
      const mockCampaigns = {
        items: [
          {
            id: '1',
            name: 'Campaign 1',
            status: 'completed',
            total_records: 100,
            processed_records: 100,
            successful_updates: 95,
            failed_updates: 5,
          },
          {
            id: '2',
            name: 'Campaign 2',
            status: 'running',
            total_records: 50,
            processed_records: 25,
            successful_updates: 20,
            failed_updates: 5,
          },
        ],
        total: 2,
      };

      vi.mocked(backfillApi.getCampaigns).mockResolvedValue(mockCampaigns);
      vi.mocked(backfillApi.getSchedules).mockResolvedValue({ items: [] });

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        // Should display total campaigns
        expect(screen.getByText('2')).toBeInTheDocument();
        
        // Should display success rate or other stats
        // (Adjust based on your actual KPI implementation)
      });
    });
  });

  describe('Campaign Table', () => {
    it('renders campaign list correctly', async () => {
      const mockCampaigns = {
        items: [
          {
            id: '1',
            name: 'Artist Bio Enrichment',
            status: 'completed',
            total_records: 100,
            processed_records: 100,
            successful_updates: 95,
            failed_updates: 5,
            created_at: '2024-01-01T00:00:00Z',
          },
          {
            id: '2',
            name: 'Venue Data Update',
            status: 'running',
            total_records: 50,
            processed_records: 25,
            successful_updates: 20,
            failed_updates: 5,
            created_at: '2024-01-02T00:00:00Z',
          },
        ],
        total: 2,
      };

      vi.mocked(backfillApi.getCampaigns).mockResolvedValue(mockCampaigns);
      vi.mocked(backfillApi.getSchedules).mockResolvedValue({ items: [] });

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Artist Bio Enrichment')).toBeInTheDocument();
        expect(screen.getByText('Venue Data Update')).toBeInTheDocument();
      });
    });

    it('displays empty state when no campaigns exist', async () => {
      vi.mocked(backfillApi.getCampaigns).mockResolvedValue({
        items: [],
        total: 0,
      });
      vi.mocked(backfillApi.getSchedules).mockResolvedValue({ items: [] });

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/no campaigns/i)).toBeInTheDocument();
      });
    });
  });

  describe('Schedule Table', () => {
    it('renders schedule list correctly', async () => {
      const mockSchedules = {
        items: [
          {
            id: '1',
            name: 'Weekly Artist Refresh',
            schedule_type: 'recurring',
            cron_expression: '0 2 * * 0',
            enabled: true,
            next_run_at: '2024-01-07T02:00:00Z',
          },
          {
            id: '2',
            name: 'Daily Venue Update',
            schedule_type: 'recurring',
            cron_expression: '0 3 * * *',
            enabled: false,
            next_run_at: '2024-01-02T03:00:00Z',
          },
        ],
      };

      vi.mocked(backfillApi.getCampaigns).mockResolvedValue({
        items: [],
        total: 0,
      });
      vi.mocked(backfillApi.getSchedules).mockResolvedValue(mockSchedules);

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Weekly Artist Refresh')).toBeInTheDocument();
        expect(screen.getByText('Daily Venue Update')).toBeInTheDocument();
      });
    });
  });

  describe('Schedule Creation Form', () => {
    it('allows user to create a new schedule', async () => {
      const user = userEvent.setup();
      
      vi.mocked(backfillApi.getCampaigns).mockResolvedValue({
        items: [],
        total: 0,
      });
      vi.mocked(backfillApi.getSchedules).mockResolvedValue({ items: [] });
      
      const mockCreateSchedule = vi.mocked(backfillApi.createSchedule)
        .mockResolvedValue({
          schedule_id: 'new-schedule-id',
          next_run_at: '2024-01-07T02:00:00Z',
        });

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create schedule/i })).toBeInTheDocument();
      });

      // Find and fill the form
      const nameInput = screen.getByLabelText(/schedule name/i);
      const cronInput = screen.getByLabelText(/cron expression/i);
      const submitButton = screen.getByRole('button', { name: /create/i });

      await user.type(nameInput, 'Test Schedule');
      await user.type(cronInput, '0 2 * * 0');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockCreateSchedule).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Test Schedule',
            cron_expression: '0 2 * * 0',
          })
        );
      });
    });

    it('displays success message after schedule creation', async () => {
      const user = userEvent.setup();
      
      vi.mocked(backfillApi.getCampaigns).mockResolvedValue({
        items: [],
        total: 0,
      });
      vi.mocked(backfillApi.getSchedules).mockResolvedValue({ items: [] });
      vi.mocked(backfillApi.createSchedule).mockResolvedValue({
        schedule_id: 'new-schedule-id',
        next_run_at: '2024-01-07T02:00:00Z',
      });

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create/i })).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /create/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/success/i)).toBeInTheDocument();
      });
    });

    it('displays error message when schedule creation fails', async () => {
      const user = userEvent.setup();
      
      vi.mocked(backfillApi.getCampaigns).mockResolvedValue({
        items: [],
        total: 0,
      });
      vi.mocked(backfillApi.getSchedules).mockResolvedValue({ items: [] });
      vi.mocked(backfillApi.createSchedule).mockRejectedValue(
        new Error('Invalid cron expression')
      );

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create/i })).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /create/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });
    });
  });

  describe('Real-time Updates', () => {
    it('refetches data after successful schedule creation', async () => {
      const user = userEvent.setup();
      
      const getCampaignsSpy = vi.mocked(backfillApi.getCampaigns)
        .mockResolvedValue({ items: [], total: 0 });
      
      const getSchedulesSpy = vi.mocked(backfillApi.getSchedules)
        .mockResolvedValue({ items: [] });
      
      vi.mocked(backfillApi.createSchedule).mockResolvedValue({
        schedule_id: 'new-schedule-id',
        next_run_at: '2024-01-07T02:00:00Z',
      });

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create/i })).toBeInTheDocument();
      });

      // Initial calls
      expect(getCampaignsSpy).toHaveBeenCalledTimes(1);
      expect(getSchedulesSpy).toHaveBeenCalledTimes(1);

      const submitButton = screen.getByRole('button', { name: /create/i });
      await user.click(submitButton);

      // Should refetch after creation
      await waitFor(() => {
        expect(getSchedulesSpy).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper heading hierarchy', async () => {
      vi.mocked(backfillApi.getCampaigns).mockResolvedValue({
        items: [],
        total: 0,
      });
      vi.mocked(backfillApi.getSchedules).mockResolvedValue({ items: [] });

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        const headings = screen.getAllByRole('heading');
        expect(headings.length).toBeGreaterThan(0);
      });
    });

    it('has accessible form labels', async () => {
      vi.mocked(backfillApi.getCampaigns).mockResolvedValue({
        items: [],
        total: 0,
      });
      vi.mocked(backfillApi.getSchedules).mockResolvedValue({ items: [] });

      render(<Backfill />, { wrapper: createWrapper() });

      await waitFor(() => {
        const nameInput = screen.getByLabelText(/schedule name/i);
        expect(nameInput).toBeInTheDocument();
      });
    });
  });
});
TSX

echo "✅ Created frontend/src/pages/__tests__/Backfill.test.tsx"

# Run the tests
echo ""
echo "=== Running Frontend Tests ==="
cd frontend
npm test -- Backfill.test.tsx

echo ""
echo "✅ Frontend tests complete"
```

### Dependencies Check

Ensure these are in `frontend/package.json`:

```json
{
  "devDependencies": {
    "@testing-library/react": "^14.0.0",
    "@testing-library/user-event": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "vitest": "^1.0.0",
    "@vitest/ui": "^1.0.0"
  }
}
```

If missing, install:

```bash
cd frontend
npm install --save-dev @testing-library/react @testing-library/user-event @testing-library/jest-dom
```

---

## TASK 3: VERIFICATION

### Verify Backend Fix

```bash
# Run the specific failing test
pytest tests/test_operations_sprints.py::test_jobs_include_runtime_visibility_fields -vv

# Run all operations tests
pytest tests/test_operations_sprints.py -vv

# Run full test suite
pytest -vv --maxfail=10 --disable-warnings
```

**Expected:** All tests pass, no timezone errors

### Verify Frontend Tests

```bash
cd frontend

# Run backfill tests only
npm test -- Backfill.test.tsx

# Run with coverage
npm test -- --coverage Backfill.test.tsx

# Run all tests
npm test
```

**Expected:** All backfill tests pass

---

## TASK 4: COMMIT CHANGES

```bash
git add app/api/routes/operations.py
git add frontend/src/pages/__tests__/Backfill.test.tsx
git commit -m "fix: resolve timezone comparison bug in operations; add Backfill.tsx tests"
git push
```

---

## SUCCESS CRITERIA

### Backend
- [ ] `test_jobs_include_runtime_visibility_fields` passes
- [ ] No timezone-related errors in any test
- [ ] All 138 tests pass

### Frontend
- [ ] `Backfill.test.tsx` created
- [ ] All test scenarios pass:
  - [ ] Loading state
  - [ ] Error handling
  - [ ] KPI cards
  - [ ] Campaign table
  - [ ] Schedule table
  - [ ] Schedule creation form
  - [ ] Success/error messages
  - [ ] Real-time updates
- [ ] Test coverage > 80% for Backfill.tsx

### Documentation
- [ ] Update `40_documentation_updates_needed.md` to mark frontend tests as complete
- [ ] Commit includes both fixes in one clean commit

---

## NOTES

### Backend Fix Options

**Option 1 (Recommended):** Make naive datetime aware
```python
if last_heartbeat.tzinfo is None:
    last_heartbeat = last_heartbeat.replace(tzinfo=UTC)
```

**Option 2:** Make both naive
```python
now = datetime.now()  # Naive
last_heartbeat = job.last_heartbeat_at  # Already naive
```

**Option 3:** Ensure DB always stores timezone-aware datetimes
- Requires migration
- More work but cleanest long-term

Choose **Option 1** for immediate fix.

### Frontend Test Adjustments

The test file is a **template** based on common patterns. You may need to adjust:

- Element selectors (based on actual component)
- Test data structure (based on actual API responses)
- Form field names (based on actual implementation)
- Success/error message text (based on actual UI)

Run tests first, then adjust based on failures.

---

Ready to execute! 🚀
