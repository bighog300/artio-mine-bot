=== DATABASE MODELS ===

**Models Found:**
676:class BackfillCampaign(Base):
709:class BackfillJob(Base):
740:class BackfillSchedule(Base):
766:class BackfillPolicy(Base):

=== DATABASE MIGRATIONS ===

**Migration Files:**
app/db/migrations/versions/a1b2c3d4e5f6_add_backfill_tables.py
app/db/migrations/versions/b2f7e91c4d11_add_backfill_schedule_policy_tables.py

=== SERVICES ===

**Service Files:**
-rw-r--r-- 1 root root 4.2K Apr 16 14:07 app/services/backfill_query.py
-rw-r--r-- 1 root root 3.9K Apr 16 14:07 app/services/completeness.py

=== PIPELINE ===

**Pipeline Files:**
-rw-r--r-- 1 root root  13K Apr 16 14:07 app/pipeline/backfill_processor.py
-rw-r--r-- 1 root root 3.9K Apr 16 14:07 app/pipeline/backfill_scheduler.py

=== API ROUTES ===

**Route Files:**
-rw-r--r-- 1 root root 15K Apr 16 14:07 app/api/routes/backfill.py

=== CLI ===

**CLI Files:**
-rw-r--r-- 1 root root 8.9K Apr 16 14:07 app/cli/backfill.py

=== FRONTEND ===

**Frontend Components:**
frontend/src/pages/Backfill.tsx
frontend/src/api/backfill.ts
