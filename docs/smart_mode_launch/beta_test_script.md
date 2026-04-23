# Smart Mode Beta Test Script

## Objective
Validate that a first-time operator can run Smart Mode from URL submission to approved records with high reliability and minimal support.

## Tester prerequisites
- Assigned beta account from `beta_testers.csv`.
- One approved source URL provided by launch coordinator.
- Browser: latest Chrome or Firefox.
- 30-minute test window.

## Test flow

### Step 1 — Login and source setup
1. Log in with beta account.
2. Open **Smart Mining** page.
3. Paste source URL and source name.
4. Submit source.

**Success criteria**
- Source saves without manual API intervention.
- Smart Mode entrypoint is visible within 10 seconds.

### Step 2 — Run Smart Mode crawl
1. Start Smart Mode mining.
2. Observe crawl + extraction progress indicators.
3. Wait for first extracted records.

**Success criteria**
- Time to first record is under 5 minutes.
- Progress status updates at least every 15 seconds.
- No blocking error modal persists > 60 seconds.

### Step 3 — Review extracted records
1. Open records table.
2. Validate at least 5 records for type and key fields.
3. Approve at least 3 records.
4. Reject or edit at least 1 low-confidence record.

**Success criteria**
- Confidence labels are shown for each record.
- Record actions (approve/reject/edit) persist immediately.

### Step 4 — Validate images and export readiness
1. Open image panel for one record.
2. Confirm image URL and thumbnail load.
3. Mark at least one record export-ready.

**Success criteria**
- Image preview loads in under 3 seconds for valid image URL.
- Export-ready state is visible in record status.

### Step 5 — Submit feedback
1. Complete post-run survey (1–5 scale + free text).
2. Report issues with severity suggestion (P0/P1/P2/P3).

**Success criteria**
- Feedback form submits successfully.
- Survey contains satisfaction score and at least one comment.

## Pass/Fail threshold per tester
- PASS: All steps complete and no unresolved P0 encountered.
- CONDITIONAL PASS: Flow completes with at most one P1 issue.
- FAIL: Unable to complete core flow (URL → first record → review).
