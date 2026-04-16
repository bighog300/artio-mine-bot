# Backfill System Documentation

Complete documentation for the Artio Backfill System - an intelligent data enrichment platform that automatically revisits discovered URLs to fill missing metadata.

---

## 📚 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Phase Documentation](#phase-documentation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [CLI Reference](#cli-reference)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Backfill System enables intelligent, targeted data enrichment for your crawler. It:

- **Scores data quality** (0-100% completeness per record)
- **Identifies gaps** (missing bio, nationality, birth_year, etc.)
- **Targets enrichment** (selective backfilling based on criteria)
- **Executes automatically** (worker-based crawling and extraction)
- **Tracks progress** (real-time monitoring and analytics)
- **Schedules campaigns** (recurring enrichment jobs)

### Use Case

You've discovered 358 artist records from directories like art.co.za and artrabbit.com. Some have basic info (name, URL) but are missing critical fields like bio, nationality, or birth year. The backfill system:

1. Calculates completeness scores (e.g., "Jane Smith is 45% complete")
2. Identifies which fields are missing
3. Creates targeted campaigns (e.g., "Artists below 70% completeness")
4. Revisits the stored URLs to crawl for missing data
5. Extracts and merges new data (preserving existing values)
6. Tracks improvements (45% → 73%, +28%)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BACKFILL SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐         ┌────────────────┐             │
│  │  Completeness  │────────▶│     Query      │             │
│  │   Calculator   │         │    Builder     │             │
│  └────────────────┘         └────────────────┘             │
│         │                           │                       │
│         │                           ▼                       │
│         │                   ┌────────────────┐             │
│         │                   │   Campaign     │             │
│         └──────────────────▶│   Manager      │             │
│                             └────────────────┘             │
│                                     │                       │
│                                     ▼                       │
│                             ┌────────────────┐             │
│                             │   RQ Worker    │             │
│                             │   Processor    │             │
│                             └────────────────┘             │
│                                     │                       │
│                    ┌────────────────┼────────────────┐     │
│                    │                │                │     │
│                    ▼                ▼                ▼     │
│              ┌─────────┐      ┌─────────┐      ┌─────────┐│
│              │ Crawler │      │Extractor│      │  Record ││
│              │         │      │         │      │ Updater ││
│              └─────────┘      └─────────┘      └─────────┘│
│                                                              │
│  ┌────────────────────────────────────────────────────────┐│
│  │              PostgreSQL Database                        ││
│  │  • backfill_campaigns                                   ││
│  │  • backfill_jobs                                        ││
│  │  • records (with completeness_score)                    ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User creates campaign
   ↓
2. System finds incomplete records
   ↓
3. Creates jobs for each record
   ↓
4. Jobs enqueued to RQ
   ↓
5. Worker picks up job
   ↓
6. Crawls URL → Extracts data → Updates record
   ↓
7. Calculates new completeness
   ↓
8. Updates campaign stats
   ↓
9. Campaign completes
```

---

## Phase Documentation

### Phase 1: Foundation ✅ **COMPLETED**
**Status**: Integrated via Codex (commit 5a142c4)

Core infrastructure for backfill system:
- Database schema (campaigns, jobs, completeness tracking)
- Completeness scoring engine
- Query builder for finding incomplete records
- REST API endpoints
- CLI commands

**Files**: 9 created, all code compiles, tests pass

📖 **[Read Phase 1 Docs](PHASE_1_FOUNDATION.md)**

---

### Phase 2: Worker Integration 🟡 **PENDING**
**Status**: Ready for implementation

Adds actual execution:
- Worker processor for job execution
- URL crawling and data extraction
- Smart data merging (only update null fields)
- Real-time progress tracking
- Live monitoring CLI

📖 **[Read Phase 2 Docs](PHASE_2_WORKER.md)**

---

### Phase 3: Scheduling & Automation 📋 **PLANNED**
**Status**: Design complete

Automation features:
- Scheduled campaigns (cron-based)
- Policy-based triggers (auto-backfill on conditions)
- Notifications (email, webhook, Slack)
- Analytics dashboard
- Background scheduler service

📖 **[Read Phase 3 Docs](PHASE_3_SCHEDULING.md)**

---

### Phase 4: Frontend Dashboard 📋 **PLANNED**
**Status**: Design complete

Complete UI:
- Dashboard overview
- Campaign management wizard
- Quality metrics visualization
- Live monitoring with WebSocket
- Analytics charts
- Schedule manager

📖 **[Read Phase 4 Docs](PHASE_4_DASHBOARD.md)**

---

## Quick Start

### Prerequisites

- Phase 1 integrated ✅
- PostgreSQL running
- Redis running
- RQ worker running

### Calculate Completeness

```bash
# First, calculate completeness for all existing records
docker compose exec api python << 'PY'
import asyncio
from app.db import async_session
from app.services.completeness import batch_update_completeness

async def run():
    async with async_session() as db:
        count = await batch_update_completeness(db)
        print(f"✅ Updated {count} records")

asyncio.run(run())
PY
```

### Create Your First Campaign

#### Via CLI

```bash
# Preview what would be backfilled
docker compose exec api python -m app.cli.backfill incomplete \
  --record-type artist \
  --max-completeness 70 \
  --limit 10 \
  --dry-run

# Create campaign
docker compose exec api python -m app.cli.backfill incomplete \
  --record-type artist \
  --max-completeness 70 \
  --limit 50

# Note the campaign ID from output, then:
# (Phase 2+ only) Start campaign
curl -X POST http://localhost:8765/api/backfill/campaigns/<campaign-id>/start

# Check status
docker compose exec api python -m app.cli.backfill status <campaign-id>
```

#### Via API

```bash
# Preview
curl "http://localhost:8765/api/backfill/preview?record_type=artist&max_completeness=70&limit=5"

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
  }'

# List campaigns
curl http://localhost:8765/api/backfill/campaigns

# Get campaign details
curl http://localhost:8765/api/backfill/campaigns/<campaign-id>
```

---

## API Reference

### Campaigns

```
GET  /api/backfill/preview
POST /api/backfill/campaigns
GET  /api/backfill/campaigns
GET  /api/backfill/campaigns/{id}
POST /api/backfill/campaigns/{id}/start
POST /api/backfill/campaigns/{id}/check-completion (Phase 2+)
DELETE /api/backfill/campaigns/{id}
```

### Analytics (Phase 3+)

```
GET /api/backfill/analytics/summary
GET /api/backfill/analytics/trends
```

### Schedules (Phase 3+)

```
GET  /api/backfill/schedules
POST /api/backfill/schedules
PUT  /api/backfill/schedules/{id}
DELETE /api/backfill/schedules/{id}
POST /api/backfill/schedules/{id}/run-now
```

### Policies (Phase 3+)

```
GET  /api/backfill/policies
POST /api/backfill/policies
PUT  /api/backfill/policies/{id}/toggle
```

---

## CLI Reference

### Phase 1 Commands

```bash
# Preview incomplete records
python -m app.cli.backfill incomplete \
  --record-type <type> \
  --min-completeness <0-100> \
  --max-completeness <0-100> \
  --limit <N> \
  --dry-run

# Preview uncrawled URLs
python -m app.cli.backfill urls \
  --record-type <type> \
  --limit <N> \
  --dry-run

# List campaigns
python -m app.cli.backfill list

# Check campaign status
python -m app.cli.backfill status <campaign-id>
```

### Phase 2 Commands

```bash
# Start campaign
python -m app.cli.backfill start <campaign-id>

# Live monitor (real-time progress)
python -m app.cli.backfill monitor --interval 5
```

### Phase 3 Commands

```bash
# Schedule management
python -m app.cli.backfill schedule create --name "..." --cron "..."
python -m app.cli.backfill schedule list
python -m app.cli.backfill schedule run-now <schedule-id>

# Policy management
python -m app.cli.backfill policy create --name "..." --trigger new_records
python -m app.cli.backfill policy list

# Analytics
python -m app.cli.backfill analytics summary
python -m app.cli.backfill analytics trends --days 30
```

---

## Development

### Running Tests

```bash
# Test completeness calculator
docker compose exec api python -c "
from app.services.completeness import calculate_completeness
from app.db.models import Record

# Create test record
record = Record(
    record_type='artist',
    title='Test Artist',
    source_url='https://example.com',
    bio=None,
    nationality=None
)

result = calculate_completeness(record)
print(f'Score: {result[\"score\"]}%')
print(f'Missing: {result[\"missing_fields\"]}')
"

# Test query builder
docker compose exec api python << 'PY'
import asyncio
from app.db import async_session
from app.services.backfill_query import BackfillQuery

async def test():
    async with async_session() as db:
        records = await BackfillQuery.find_incomplete_records(
            db, record_type='artist', max_completeness=70, limit=5
        )
        print(f'Found {len(records)} incomplete records')

asyncio.run(test())
PY
```

### Database Migrations

```bash
# Create new migration
docker compose exec api alembic revision -m "description"

# Apply migrations
docker compose exec api alembic upgrade head

# Rollback last migration
docker compose exec api alembic downgrade -1

# View migration history
docker compose exec api alembic history
```

### Monitoring Logs

```bash
# API logs
docker compose logs api -f

# Worker logs (Phase 2+)
docker compose logs worker -f | grep -i backfill

# Database queries
docker compose exec db psql -U postgres -d artio -c "
SELECT * FROM backfill_campaigns ORDER BY created_at DESC LIMIT 5;
"
```

---

## Troubleshooting

### Migration Issues

```bash
# Check current version
docker compose exec api alembic current

# Check for pending migrations
docker compose exec api alembic heads

# Force upgrade
docker compose exec api alembic upgrade head --sql  # Preview SQL
docker compose exec api alembic upgrade head        # Execute
```

### API Endpoints Not Found

```bash
# Verify routes are registered
docker compose exec api python -c "
from app.api.main import app
for route in app.routes:
    if hasattr(route, 'path') and 'backfill' in route.path:
        print(route.path)
"

# Check imports
docker compose logs api | grep -i backfill | grep -i error
```

### Import Errors

```bash
# Test imports
docker compose exec api python -c "
from app.services.completeness import calculate_completeness
from app.services.backfill_query import BackfillQuery
from app.db.models import BackfillCampaign, BackfillJob
print('✅ All imports successful')
"
```

### Worker Not Processing Jobs (Phase 2+)

```bash
# Check worker status
docker compose ps worker

# Check RQ connection
docker compose exec api python -c "
from redis import Redis
from app.config import settings
r = Redis.from_url(settings.REDIS_URL)
print(f'Redis connected: {r.ping()}')
"

# Check queue
docker compose exec api python -c "
from redis import Redis
from rq import Queue
from app.config import settings

r = Redis.from_url(settings.REDIS_URL)
q = Queue('default', connection=r)
print(f'Jobs in queue: {len(q)}')
"
```

### Jobs Failing (Phase 2+)

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
            print(f"Job: {job.id}")
            print(f"URL: {job.url_to_crawl}")
            print(f"Error: {job.error_message}")
            print()

asyncio.run(check())
PY
```

---

## Performance Tuning

### Batch Size

```python
# Adjust in campaign options
{
  "options": {
    "batch_size": 50,  # Process 50 jobs at a time
    "limit": 1000
  }
}
```

### Worker Concurrency

```yaml
# docker-compose.yml
worker:
  command: python -m app.pipeline.runner --concurrency 4
```

### Database Indexing

```sql
-- Verify indexes exist
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename IN ('backfill_campaigns', 'backfill_jobs');

-- Add custom indexes if needed
CREATE INDEX idx_campaigns_status_created 
ON backfill_campaigns(status, created_at DESC);
```

---

## Support & Resources

**Documentation**: 
- Phase 1: [PHASE_1_FOUNDATION.md](PHASE_1_FOUNDATION.md)
- Phase 2: [PHASE_2_WORKER.md](PHASE_2_WORKER.md)
- Phase 3: [PHASE_3_SCHEDULING.md](PHASE_3_SCHEDULING.md)
- Phase 4: [PHASE_4_DASHBOARD.md](PHASE_4_DASHBOARD.md)

**Integration Guides**:
- [INTEGRATION_INSTRUCTIONS.md](../INTEGRATION_INSTRUCTIONS.md)
- [PHASE2_WORKER_INTEGRATION.md](../PHASE2_WORKER_INTEGRATION.md)

**Original Design**: [BACKFILL_SYSTEM_DESIGN.md](../BACKFILL_SYSTEM_DESIGN.md)

---

## License

Part of the Artio Mine Bot project.

---

**System Status**: Phase 1 Complete ✅ | Phase 2 Ready 🟡 | Phase 3-4 Planned 📋

Built with ❤️ for intelligent data enrichment
