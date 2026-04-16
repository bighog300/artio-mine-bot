# Phase 2: Worker Integration

## Overview

Phase 2 adds actual execution capabilities to the backfill system. When campaigns are started, jobs are enqueued to RQ workers which crawl URLs, extract missing data, and enrich records.

**Status**: 🟡 PENDING INTEGRATION

**Prerequisites**: Phase 1 must be completed and verified

---

## What Phase 2 Delivers

### 1. Backfill Processor

**Core Worker Module** (`app/pipeline/backfill_processor.py`):

**Key Functions:**

- `enqueue_backfill_campaign(db, campaign_id)` 
  - Pushes all pending jobs to RQ queue
  - Returns count of jobs enqueued

- `process_backfill_job(job_id)`
  - Main worker function (called by RQ)
  - Crawls URL, extracts data, updates record
  - Tracks before/after completeness

- `check_campaign_completion(db, campaign_id)`
  - Checks if all jobs done
  - Updates campaign status to "completed"

### 2. Job Execution Flow

```
1. Campaign Started
   ↓
2. Jobs Enqueued to RQ
   ↓
3. Worker Picks Up Job
   ↓
4. Crawl URL (create Page if needed)
   ↓
5. Extract Data from HTML
   ↓
6. Merge into Record (only update null fields)
   ↓
7. Calculate New Completeness
   ↓
8. Update Job Status & Campaign Stats
   ↓
9. Check Campaign Completion
```

### 3. Data Extraction

**Extraction Strategy:**

1. **Try existing extractor** - Use `app.pipeline.extractor.extract_structured_data()` if available
2. **Fallback to BeautifulSoup** - Simple pattern-based extraction
3. **Record what was found** - Track which fields were updated

**Example Extraction (Artist):**
```python
# Look for bio in common selectors
bio_selectors = [
    'div.biography', 'div.bio', 'div.about',
    'section.biography', 'p.bio'
]

# Look for website in links
for link in soup.find_all('a'):
    if 'website' in link.text.lower():
        data['website_url'] = link['href']
```

### 4. Smart Data Merging

**Merge Logic:**
```python
# Only update fields that are currently null/empty
for field, new_value in extracted_data.items():
    current_value = getattr(record, field)
    
    if current_value is None or current_value == "" or current_value == "[]":
        setattr(record, field, new_value)
        fields_updated.append(field)
```

**Why This Matters:**
- Preserves manually curated data
- Doesn't overwrite good data with bad
- Allows incremental enrichment

### 5. Progress Tracking

**Real-time Updates:**
- Job status: pending → running → completed/failed
- Campaign stats: processed_records, successful_updates, failed_updates
- Before/after completeness comparison
- Field-level change tracking

**Example Progress:**
```
Backfilling artist 'Jane Smith' from https://art.co.za/artists/jane-smith
✅ Completed: Jane Smith (45% → 73%, +28%)
   Updated fields: bio, nationality, birth_year
```

### 6. Error Handling

**Failure Management:**
- Jobs that fail are marked with error message
- Campaign continues processing other jobs
- Failed jobs can be retried manually
- Errors logged for debugging

**Error Types:**
- Network failures (timeout, 404, etc.)
- Parse failures (invalid HTML)
- Extraction failures (no data found)
- Database failures (record not found)

### 7. Monitoring Tools

**Live Monitor CLI:**
```bash
docker compose exec api python -m app.cli.backfill monitor
```

**Output:**
```
================================================================================
Backfill Campaigns Monitor - 2026-04-16 14:23:15 UTC
================================================================================

Artist Bio Enrichment
  ID: abc-123-def-456
  Progress: 32/50 (64%)
  Successful: 29 | Failed: 3
  [█████████████████████████░░░░░░░░░░░░░░░] 64%

Refreshing every 5s... (Ctrl+C to stop)
```

### 8. API Enhancements

**New Endpoint:**
```
POST /api/backfill/campaigns/{id}/check-completion
  - Manually trigger completion check
  - Returns updated campaign status
```

**Updated Endpoint:**
```
POST /api/backfill/campaigns/{id}/start
  - Now actually enqueues jobs to RQ
  - Returns: jobs_enqueued count
```

---

## Files Created/Modified

```
app/
├── pipeline/
│   └── backfill_processor.py    # NEW: Worker execution logic
├── api/
│   └── routes/
│       └── backfill.py           # MODIFIED: Enqueue jobs on start
└── cli/
    └── backfill.py               # MODIFIED: Add monitor command
```

---

## Integration Steps

### 1. Add Processor Module

Create `app/pipeline/backfill_processor.py` with:
- Job enqueuing logic
- Worker execution function
- Crawling integration
- Data extraction & merging
- Progress tracking

### 2. Update API Routes

Modify `start_backfill_campaign()` to:
```python
from app.pipeline.backfill_processor import enqueue_backfill_campaign

jobs_enqueued = await enqueue_backfill_campaign(db, campaign_id)
```

### 3. Add Monitoring Command

Add to `app/cli/backfill.py`:
```python
@backfill.command()
def monitor(interval=5):
    """Monitor running campaigns in real-time"""
    # Live progress display with refresh
```

### 4. Rebuild & Restart

```bash
docker compose build api worker
docker compose restart api worker
```

---

## Example Usage

### Complete Workflow

```bash
# 1. Create campaign (Phase 1)
docker compose exec api python -m app.cli.backfill incomplete \
  --record-type artist \
  --max-completeness 70 \
  --limit 50

# Campaign ID: abc-123-def

# 2. Start campaign (Phase 2 - actually executes!)
curl -X POST http://localhost:8765/api/backfill/campaigns/abc-123-def/start

# Response:
# {
#   "campaign_id": "abc-123-def",
#   "status": "started",
#   "total_jobs": 50,
#   "message": "Campaign started. 50 jobs enqueued to workers."
# }

# 3. Monitor progress in real-time
docker compose exec api python -m app.cli.backfill monitor

# 4. Watch worker logs
docker compose logs worker -f

# Output:
# Backfilling artist 'John Doe' from https://art.co.za/artists/john-doe
# ✅ Completed: John Doe (60% → 82%, +22%)
#    Updated fields: bio, website_url, instagram_url

# 5. Check final status
docker compose exec api python -m app.cli.backfill status abc-123-def

# Output:
# Campaign: Artist Bio Enrichment
# Status: COMPLETED
# Progress:
#   Total records: 50
#   Processed: 50
#   Successful: 47
#   Failed: 3
#   Progress: 100%
```

### API Usage

```bash
# Start campaign
curl -X POST http://localhost:8765/api/backfill/campaigns/abc-123-def/start \
  | python3 -m json.tool

# Check completion
curl -X POST http://localhost:8765/api/backfill/campaigns/abc-123-def/check-completion \
  | python3 -m json.tool

# Get status
curl http://localhost:8765/api/backfill/campaigns/abc-123-def \
  | python3 -m json.tool
```

---

## Verification Checklist

Phase 2 is complete when:

- [ ] `app/pipeline/backfill_processor.py` exists and imports successfully
- [ ] Starting campaign enqueues jobs to RQ
- [ ] Worker processes jobs (visible in logs)
- [ ] Records are actually updated with new data
- [ ] Completeness scores improve after backfill
- [ ] Campaign status changes to "completed" when done
- [ ] Monitor command shows live progress
- [ ] Failed jobs are logged with error messages

---

## Expected Results

### Before Backfill

```json
{
  "id": "rec-123",
  "record_type": "artist",
  "title": "Jane Smith",
  "source_url": "https://art.co.za/artists/jane-smith",
  "bio": null,
  "nationality": null,
  "birth_year": null,
  "website_url": null,
  "completeness_score": 45
}
```

### After Backfill

```json
{
  "id": "rec-123",
  "record_type": "artist",
  "title": "Jane Smith",
  "source_url": "https://art.co.za/artists/jane-smith",
  "bio": "Contemporary artist based in Cape Town, known for...",
  "nationality": "South African",
  "birth_year": 1985,
  "website_url": "https://janesmith.art",
  "completeness_score": 73
}
```

### Campaign Results

```
Campaign: Artist Bio Enrichment
Status: COMPLETED

Stats:
  Total records: 50
  Processed: 50
  Successful: 47 (94%)
  Failed: 3 (6%)

Average Improvement: +28%

Top Improvements:
  1. Jane Smith: 45% → 73% (+28%)
  2. John Doe: 60% → 82% (+22%)
  3. Mary Johnson: 52% → 75% (+23%)
```

---

## Performance Considerations

### Crawling

- Respects robots.txt
- Rate limiting (via existing crawler)
- Reuses cached Page records when available
- Creates new Page records for tracking

### Database

- Batch commits (every 100 records)
- Async database operations
- Indexed queries for campaign/job lookup

### Queue Management

- Jobs processed in parallel by workers
- Failed jobs don't block queue
- Retries configurable (default: 3 attempts)

---

## Troubleshooting

### Jobs Not Processing

```bash
# Check worker status
docker compose ps worker

# Verify worker logs
docker compose logs worker --tail 50

# Check RQ connection
docker compose exec api python -c "
from redis import Redis
from app.config import settings
r = Redis.from_url(settings.REDIS_URL)
print(f'Redis connected: {r.ping()}')
"
```

### Jobs Failing

```bash
# View failed jobs
docker compose exec api python << 'PY'
import asyncio
from app.db import async_session
from sqlalchemy import select
from app.db.models import BackfillJob

async def check():
    async with async_session() as db:
        stmt = select(BackfillJob).where(
            BackfillJob.status == "failed"
        ).limit(10)
        result = await db.execute(stmt)
        jobs = result.scalars().all()
        
        for job in jobs:
            print(f"\nJob: {job.id}")
            print(f"URL: {job.url_to_crawl}")
            print(f"Error: {job.error_message}")

asyncio.run(check())
PY
```

### Extraction Not Working

```bash
# Test extraction on a single URL
docker compose exec api python << 'PY'
import asyncio
from app.db import async_session
from app.pipeline.backfill_processor import _crawl_url, _extract_record_data

async def test():
    async with async_session() as db:
        html = await _crawl_url("https://art.co.za", "test", db)
        data = await _extract_record_data(html, "artist", "test")
        print(f"Extracted: {data}")

asyncio.run(test())
PY
```

---

## Integration with Existing Systems

### Crawler Integration

```python
from app.pipeline.crawler import fetch_page

# Reuses existing crawler logic
page_data = await fetch_page(url)
html = page_data["html"]
```

### Extractor Integration

```python
from app.pipeline.extractor import extract_structured_data

# Uses existing extraction rules if available
extracted = await extract_structured_data(html, record_type)
```

### Fallback Extraction

If existing extractor not available, uses BeautifulSoup:
```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, 'html.parser')
# Pattern-based extraction
```

---

## Success Metrics

After Phase 2 integration, you should see:

- **Completeness Improvement**: Average +20-30% per record
- **Success Rate**: 85-95% of jobs complete successfully
- **Processing Speed**: ~10-50 records per minute (depends on sites)
- **Data Quality**: Missing fields filled with accurate data

---

## Next Steps

After Phase 2 verification:

1. ✅ Run test campaign with small batch (5-10 records)
2. ✅ Verify data quality of backfilled records
3. ✅ Check worker logs for errors
4. → **Proceed to Phase 3** for scheduled campaigns

---

## Support

**Logs**: `docker compose logs worker -f`
**Monitoring**: `python -m app.cli.backfill monitor`
**Documentation**: See PHASE2_WORKER_INTEGRATION.md

Phase 2 brings your backfill system to life with actual data enrichment! 🚀
