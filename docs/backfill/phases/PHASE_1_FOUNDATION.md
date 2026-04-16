# Phase 1: Backfill System Foundation

## Overview

Phase 1 establishes the complete infrastructure for the backfill system without worker execution. This includes database schema, API endpoints, CLI commands, and data quality scoring.

**Status**: ✅ COMPLETED (Integrated via Codex commit 5a142c4)

---

## What Phase 1 Delivers

### 1. Database Schema

**New Tables:**
- `backfill_campaigns` - Tracks backfill operations
- `backfill_jobs` - Individual record enrichment tasks

**Enhanced Tables:**
- `records.completeness_score` - Data quality percentage (0-100)
- `records.completeness_details` - JSON of missing fields

**Migration**: `a1b2c3d4e5f6_add_backfill_tables.py`

### 2. Data Quality System

**Completeness Calculator** (`app/services/completeness.py`):
- Scores records 0-100% based on field population
- Identifies critical vs optional missing fields
- Field definitions per record type:
  ```
  artist:
    critical: [title, source_url]
    important: [bio, nationality, birth_year, website_url]
    optional: [instagram_url, email, avatar_url, mediums, collections]
  ```

**Functions:**
- `calculate_completeness(record)` - Score single record
- `update_record_completeness(db, record)` - Update and commit
- `batch_update_completeness(db, record_type)` - Update all records

### 3. Query Builder

**Backfill Query Service** (`app/services/backfill_query.py`):

Finds records needing backfill using multiple strategies:

- `find_incomplete_records()` - Records with low completeness scores
- `find_uncrawled_urls()` - URLs discovered but not yet crawled
- `find_stale_records()` - Data older than N days
- `find_records_by_source()` - All records from specific source

### 4. REST API

**Endpoints** (`/api/backfill/*`):

```
GET  /api/backfill/preview
  - Dry-run preview of what would be backfilled
  - Query params: record_type, min_completeness, max_completeness, limit

POST /api/backfill/campaigns
  - Create new backfill campaign
  - Body: {name, strategy, filters, options}

GET  /api/backfill/campaigns
  - List all campaigns
  - Query params: limit, skip

GET  /api/backfill/campaigns/{id}
  - Get campaign details and progress
  - Returns: stats, job_stats, filters, options

POST /api/backfill/campaigns/{id}/start
  - Start campaign execution (enqueues jobs in Phase 2)

DELETE /api/backfill/campaigns/{id}
  - Delete campaign (only if not running)
```

### 5. CLI Interface

**Commands** (`python -m app.cli.backfill`):

```bash
# Preview incomplete records
backfill incomplete --record-type artist --max-completeness 70 --dry-run

# Preview uncrawled URLs
backfill urls --record-type artist --dry-run

# List all campaigns
backfill list

# Check campaign status
backfill status <campaign-id>
```

### 6. ORM Models

**BackfillCampaign**:
- Tracks campaign lifecycle (pending → running → completed)
- Stores filters and options as JSON
- Maintains statistics (total, processed, successful, failed)

**BackfillJob**:
- Individual job per record
- Tracks before/after completeness
- Records which fields were updated
- Supports retries and error logging

---

## Files Created

```
app/
├── services/
│   ├── __init__.py
│   ├── completeness.py          # Data quality scoring
│   └── backfill_query.py        # Query builder
├── api/
│   └── routes/
│       └── backfill.py           # REST endpoints
├── cli/
│   ├── __init__.py
│   └── backfill.py               # CLI commands
└── db/
    ├── models.py                 # Added BackfillCampaign & BackfillJob
    └── migrations/
        └── versions/
            └── a1b2c3d4e5f6_add_backfill_tables.py
```

---

## Example Usage

### Via CLI

```bash
# 1. Calculate completeness for existing records
docker compose exec api python << 'PY'
import asyncio
from app.db import async_session
from app.services.completeness import batch_update_completeness

async def run():
    async with async_session() as db:
        count = await batch_update_completeness(db)
        print(f"Updated {count} records")

asyncio.run(run())
PY

# 2. Preview what needs backfilling
docker compose exec api python -m app.cli.backfill incomplete \
  --record-type artist \
  --max-completeness 70 \
  --limit 10 \
  --dry-run

# Output:
# Found 87 incomplete records
# 1. ARTIST: Jane Smith
#    URL: https://art.co.za/artists/jane-smith
#    Completeness: 45%
#    Missing: bio, nationality, birth_year, instagram_url, email

# 3. Create campaign
docker compose exec api python -m app.cli.backfill incomplete \
  --record-type artist \
  --max-completeness 70 \
  --limit 50

# Output:
# ✅ Campaign created: abc-123-def
#    Name: Incomplete artist - 0-70%
#    Total records: 50

# 4. List campaigns
docker compose exec api python -m app.cli.backfill list
```

### Via API

```bash
# Preview
curl "http://localhost:8765/api/backfill/preview?record_type=artist&max_completeness=70&limit=5" \
  | python3 -m json.tool

# Create campaign
curl -X POST http://localhost:8765/api/backfill/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Artist Bio Enrichment",
    "strategy": "selective",
    "filters": {
      "record_type": "artist",
      "completeness_range": [0, 70]
    },
    "options": {
      "limit": 100
    }
  }' | python3 -m json.tool

# List campaigns
curl http://localhost:8765/api/backfill/campaigns | python3 -m json.tool

# Check status
curl http://localhost:8765/api/backfill/campaigns/{id} | python3 -m json.tool
```

---

## Verification Checklist

Phase 1 is complete when:

- [x] Migration creates `backfill_campaigns` and `backfill_jobs` tables
- [x] Completeness scores calculated for all records
- [x] Preview endpoint returns incomplete records
- [x] Can create campaigns via CLI and API
- [x] Can list and view campaign details
- [x] No errors in API logs
- [x] All code compiles successfully

---

## What Phase 1 Does NOT Include

⚠️ **Phase 1 creates infrastructure but does NOT execute crawling**:

- Campaigns can be created ✅
- Jobs are tracked in database ✅
- Starting campaign updates status ✅
- **BUT**: No actual crawling happens ❌
- **BUT**: Records are not enriched ❌

**Phase 2** adds worker integration to actually execute backfill jobs.

---

## Technical Details

### Completeness Scoring Algorithm

```python
# For each record type, define fields
fields = {
    "critical": [...],   # Must-have fields
    "important": [...],  # Should-have fields
    "optional": [...]    # Nice-to-have fields
}

# Check which fields are populated
populated = [f for f in all_fields if value_exists(record[f])]

# Calculate score
score = (len(populated) / len(all_fields)) * 100
```

### Campaign Strategies

1. **Selective**: Target records with specific completeness ranges
2. **URL-based**: Crawl discovered URLs not yet visited
3. **Time-based**: Refresh stale data (older than N days)
4. **Source**: Re-crawl all records from a specific source

### Job Lifecycle

```
pending → running → completed/failed
```

Jobs track:
- URL to crawl
- Before completeness score
- After completeness score
- Fields that were updated
- Error messages (if failed)
- Attempt count

---

## Performance Considerations

- Batch completeness updates in groups of 100
- Campaigns limited to 1000 records by default
- Database indexes on campaign/job status for fast queries
- JSON fields for flexible filter storage

---

## Next Steps

After Phase 1 integration:

1. ✅ Verify all endpoints work
2. ✅ Calculate completeness for existing data
3. ✅ Create test campaigns
4. → **Proceed to Phase 2** for worker integration

---

## Support

**Documentation**: See INTEGRATION_INSTRUCTIONS.md
**Issues**: Check troubleshooting section in main docs
**Testing**: Run verification commands above

Phase 1 provides the complete foundation for intelligent, targeted data enrichment! 🎯
