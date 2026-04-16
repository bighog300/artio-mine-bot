# Phase 3: Scheduled Campaigns & Automation

## Overview

Phase 3 adds automation and scheduling capabilities to the backfill system. Run campaigns automatically on schedules, set up recurring enrichment jobs, and maintain data freshness.

**Status**: 📋 PLANNED

**Prerequisites**: Phases 1 & 2 must be completed and verified

---

## What Phase 3 Delivers

### 1. Campaign Scheduling

**Scheduled Campaign Model** (`BackfillSchedule`):
- Define recurring backfill campaigns
- Cron-style scheduling (daily, weekly, monthly)
- Auto-create campaigns on schedule
- Track execution history

**Schedule Types:**
- **One-time**: Run once at specific time
- **Recurring**: Daily/weekly/monthly patterns
- **Conditional**: Run when criteria met (e.g., X new records)

### 2. Auto-Discovery Campaigns

**Smart Triggers:**
- New records detected → Auto-backfill incomplete ones
- Completeness drops below threshold → Trigger refresh
- Source updated → Re-crawl changed records
- Time-based → Weekly freshness updates

### 3. Backfill Policies

**Policy Engine** (`app/services/backfill_policy.py`):

Define rules like:
```python
{
  "name": "Artist Enrichment Policy",
  "trigger": "new_records",
  "conditions": {
    "record_type": "artist",
    "completeness_below": 70,
    "min_records": 10
  },
  "action": {
    "create_campaign": true,
    "auto_start": true,
    "strategy": "selective"
  }
}
```

### 4. Scheduler Service

**Background Scheduler** (`app/pipeline/backfill_scheduler.py`):
- Check schedules every minute
- Create campaigns when due
- Start campaigns if auto_start enabled
- Send notifications on completion

### 5. Notification System

**Alerts & Reports:**
- Email/webhook on campaign completion
- Slack/Discord integration
- Summary reports (daily/weekly)
- Alert on high failure rates

### 6. Dashboard API

**Analytics Endpoints:**
```
GET /api/backfill/analytics/summary
  - Overall backfill statistics
  - Success rates, avg improvement
  - Top improved records

GET /api/backfill/analytics/trends
  - Completeness trends over time
  - Campaign success rates by type
  - Processing speed metrics

GET /api/backfill/schedules
  - List all scheduled campaigns
  
POST /api/backfill/schedules
  - Create new schedule
  
PUT /api/backfill/schedules/{id}
  - Update schedule
  
DELETE /api/backfill/schedules/{id}
  - Delete schedule
```

---

## Database Schema

### New Tables

**backfill_schedules**:
```sql
CREATE TABLE backfill_schedules (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    schedule_type VARCHAR NOT NULL,  -- one_time, recurring, conditional
    cron_expression VARCHAR,         -- For recurring schedules
    filters_json TEXT NOT NULL,
    options_json TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    auto_start BOOLEAN DEFAULT false,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    INDEX ix_schedules_enabled (enabled),
    INDEX ix_schedules_next_run (next_run_at)
);
```

**backfill_policies**:
```sql
CREATE TABLE backfill_policies (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    trigger_type VARCHAR NOT NULL,  -- new_records, completeness_drop, time_based
    conditions_json TEXT NOT NULL,
    action_json TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    INDEX ix_policies_enabled (enabled)
);
```

**backfill_notifications**:
```sql
CREATE TABLE backfill_notifications (
    id VARCHAR PRIMARY KEY,
    campaign_id VARCHAR NOT NULL,
    notification_type VARCHAR NOT NULL,  -- email, webhook, slack
    recipient VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'pending',
    sent_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (campaign_id) REFERENCES backfill_campaigns(id)
);
```

---

## Example Configurations

### 1. Weekly Artist Enrichment

```json
{
  "name": "Weekly Artist Data Refresh",
  "schedule_type": "recurring",
  "cron_expression": "0 2 * * 0",  // 2 AM every Sunday
  "filters": {
    "record_type": "artist",
    "completeness_range": [0, 80]
  },
  "options": {
    "limit": 100,
    "auto_start": true
  },
  "notification": {
    "type": "email",
    "recipient": "admin@example.com",
    "on_complete": true
  }
}
```

### 2. New Records Auto-Backfill

```json
{
  "name": "New Artist Auto-Enrichment",
  "trigger_type": "new_records",
  "conditions": {
    "record_type": "artist",
    "completeness_below": 60,
    "min_records": 5,
    "within_hours": 24
  },
  "action": {
    "create_campaign": true,
    "auto_start": true,
    "strategy": "selective"
  }
}
```

### 3. Stale Data Refresh

```json
{
  "name": "Monthly Data Freshness",
  "schedule_type": "recurring",
  "cron_expression": "0 3 1 * *",  // 3 AM on 1st of month
  "filters": {
    "record_type": "artist",
    "older_than_days": 90
  },
  "options": {
    "limit": 500,
    "auto_start": true
  }
}
```

---

## Implementation Files

### 1. Scheduler Service

`app/pipeline/backfill_scheduler.py`:
```python
class BackfillScheduler:
    """Background service to run scheduled campaigns"""
    
    async def check_schedules(self):
        """Check for schedules that need to run"""
        # Get schedules where next_run_at <= now
        # Create campaigns for them
        # Update next_run_at based on cron
    
    async def check_policies(self):
        """Check for policy triggers"""
        # Check each policy's conditions
        # If met, execute action
    
    async def start(self):
        """Start background scheduler loop"""
        while True:
            await self.check_schedules()
            await self.check_policies()
            await asyncio.sleep(60)  # Check every minute
```

### 2. Policy Engine

`app/services/backfill_policy.py`:
```python
class BackfillPolicyEngine:
    """Evaluate and execute backfill policies"""
    
    async def evaluate_policy(self, policy: BackfillPolicy):
        """Check if policy conditions are met"""
        if policy.trigger_type == "new_records":
            return await self._check_new_records(policy.conditions)
        elif policy.trigger_type == "completeness_drop":
            return await self._check_completeness_drop(policy.conditions)
        # etc.
    
    async def execute_policy(self, policy: BackfillPolicy):
        """Execute policy action"""
        if policy.action.create_campaign:
            campaign = await self._create_campaign_from_policy(policy)
            if policy.action.auto_start:
                await enqueue_backfill_campaign(db, campaign.id)
```

### 3. Notification Service

`app/services/backfill_notifications.py`:
```python
class BackfillNotifier:
    """Send notifications about campaign completion"""
    
    async def notify_completion(self, campaign_id: str):
        """Send completion notification"""
        # Get campaign details
        # Format message
        # Send via configured channels
    
    async def send_email(self, recipient: str, campaign: BackfillCampaign):
        """Send email notification"""
        subject = f"Backfill Complete: {campaign.name}"
        body = f"""
        Campaign: {campaign.name}
        Status: {campaign.status}
        Processed: {campaign.processed_records}/{campaign.total_records}
        Success Rate: {campaign.successful_updates/campaign.total_records*100}%
        """
        # Send email
    
    async def send_webhook(self, url: str, campaign: BackfillCampaign):
        """Send webhook notification"""
        payload = {
            "campaign_id": campaign.id,
            "name": campaign.name,
            "status": campaign.status,
            "stats": {
                "total": campaign.total_records,
                "successful": campaign.successful_updates,
                "failed": campaign.failed_updates
            }
        }
        # POST to webhook URL
```

---

## API Endpoints

### Schedule Management

```python
@router.post("/schedules")
async def create_schedule(
    name: str,
    schedule_type: str,
    cron_expression: Optional[str],
    filters: dict,
    options: dict,
    auto_start: bool = False
):
    """Create new backfill schedule"""
    # Validate cron expression
    # Create schedule record
    # Calculate next_run_at
    # Return schedule

@router.get("/schedules")
async def list_schedules(enabled_only: bool = True):
    """List all schedules"""
    # Query schedules
    # Return with next run times

@router.put("/schedules/{id}")
async def update_schedule(id: str, updates: dict):
    """Update schedule configuration"""
    # Update schedule
    # Recalculate next_run_at if cron changed

@router.delete("/schedules/{id}")
async def delete_schedule(id: str):
    """Delete schedule"""
    # Mark as disabled or delete

@router.post("/schedules/{id}/run-now")
async def run_schedule_now(id: str):
    """Manually trigger scheduled campaign"""
    # Create campaign from schedule
    # Start immediately
```

### Policy Management

```python
@router.post("/policies")
async def create_policy(
    name: str,
    trigger_type: str,
    conditions: dict,
    action: dict
):
    """Create new backfill policy"""

@router.get("/policies")
async def list_policies():
    """List all policies"""

@router.put("/policies/{id}/toggle")
async def toggle_policy(id: str):
    """Enable/disable policy"""
```

### Analytics

```python
@router.get("/analytics/summary")
async def get_analytics_summary():
    """Overall backfill statistics"""
    return {
        "total_campaigns": 45,
        "total_records_processed": 2500,
        "avg_improvement": 28,
        "success_rate": 94,
        "recent_campaigns": [...]
    }

@router.get("/analytics/trends")
async def get_analytics_trends(
    start_date: str,
    end_date: str
):
    """Completeness trends over time"""
    return {
        "dates": ["2026-01-01", "2026-01-02", ...],
        "avg_completeness": [65, 67, 70, ...],
        "campaigns_run": [2, 1, 3, ...]
    }
```

---

## CLI Commands

```bash
# Schedule management
backfill schedule create \
  --name "Weekly Artist Refresh" \
  --cron "0 2 * * 0" \
  --record-type artist \
  --max-completeness 80 \
  --auto-start

backfill schedule list

backfill schedule disable <schedule-id>

backfill schedule run-now <schedule-id>

# Policy management
backfill policy create \
  --name "Auto-enrich new artists" \
  --trigger new_records \
  --min-records 5 \
  --auto-start

backfill policy list

# Analytics
backfill analytics summary

backfill analytics trends --days 30
```

---

## Integration Steps

### 1. Database Migration

```bash
# Create migration for new tables
docker compose exec api alembic revision -m "add_backfill_schedules_and_policies"

# Apply migration
docker compose exec api alembic upgrade head
```

### 2. Add Models

Add to `app/db/models.py`:
- `BackfillSchedule`
- `BackfillPolicy`
- `BackfillNotification`

### 3. Create Services

- `app/pipeline/backfill_scheduler.py`
- `app/services/backfill_policy.py`
- `app/services/backfill_notifications.py`

### 4. Add API Routes

Extend `app/api/routes/backfill.py`:
- Schedule endpoints
- Policy endpoints
- Analytics endpoints

### 5. Add CLI Commands

Extend `app/cli/backfill.py`:
- `schedule` subcommands
- `policy` subcommands
- `analytics` subcommands

### 6. Start Scheduler

Add to `docker-compose.yml`:
```yaml
scheduler:
  build: .
  command: python -m app.pipeline.backfill_scheduler
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - REDIS_URL=${REDIS_URL}
  depends_on:
    - db
    - redis
```

---

## Example Workflow

### Setup Weekly Enrichment

```bash
# 1. Create schedule
curl -X POST http://localhost:8765/api/backfill/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weekly Artist Enrichment",
    "schedule_type": "recurring",
    "cron_expression": "0 2 * * 0",
    "filters": {
      "record_type": "artist",
      "completeness_range": [0, 80]
    },
    "options": {
      "limit": 100,
      "auto_start": true
    }
  }'

# 2. Schedule runs automatically every Sunday at 2 AM

# 3. View analytics
curl http://localhost:8765/api/backfill/analytics/summary

# Output:
# {
#   "total_campaigns": 12,
#   "total_records_processed": 850,
#   "avg_improvement": 32,
#   "success_rate": 96
# }
```

### Setup Auto-Enrichment Policy

```bash
# Create policy for new records
curl -X POST http://localhost:8765/api/backfill/policies \
  -d '{
    "name": "Auto-enrich new artists",
    "trigger_type": "new_records",
    "conditions": {
      "record_type": "artist",
      "completeness_below": 60,
      "min_records": 10,
      "within_hours": 24
    },
    "action": {
      "create_campaign": true,
      "auto_start": true
    }
  }'

# Policy now runs automatically when conditions met
```

---

## Monitoring & Alerts

### Email Notifications

Configure in `app/config.py`:
```python
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-email@gmail.com"
SMTP_PASSWORD = "your-password"
NOTIFICATION_EMAIL = "admin@example.com"
```

### Webhook Integration

```bash
# Add webhook to campaign
curl -X POST http://localhost:8765/api/backfill/campaigns/{id}/notifications \
  -d '{
    "type": "webhook",
    "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "on_complete": true
  }'
```

### Slack Integration

```python
# Slack notification format
{
  "text": "Backfill Campaign Complete",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Artist Bio Enrichment*\n✅ Completed successfully"
      }
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Processed:*\n50/50"},
        {"type": "mrkdwn", "text": "*Success Rate:*\n94%"},
        {"type": "mrkdwn", "text": "*Avg Improvement:*\n+28%"}
      ]
    }
  ]
}
```

---

## Performance & Scalability

### Scheduler Optimization

- Batch schedule checks (100 at a time)
- Index on `next_run_at` for fast queries
- Cache active schedules in Redis

### Policy Evaluation

- Evaluate policies every 5 minutes (configurable)
- Skip disabled policies
- Debounce triggers (don't run same policy twice in 1 hour)

### Analytics Caching

- Cache summary stats for 5 minutes
- Pre-calculate daily aggregates
- Use database views for trends

---

## Success Criteria

Phase 3 is complete when:

- [ ] Can create and manage schedules via API/CLI
- [ ] Scheduled campaigns run automatically
- [ ] Policies trigger on conditions
- [ ] Notifications sent on completion
- [ ] Analytics endpoints return accurate data
- [ ] Scheduler runs as background service
- [ ] No performance degradation with multiple schedules

---

## Next Steps

After Phase 3:

1. ✅ Verify scheduled campaigns execute
2. ✅ Test policy triggers
3. ✅ Confirm notifications work
4. → **Proceed to Phase 4** for UI dashboard

---

Phase 3 makes your backfill system fully automated and production-grade! 🤖
