# How to Use Smart Mode

## What Smart Mode does
Smart Mode automates source setup, crawl, classification, and extraction so you can get reviewable art records quickly from a website URL.

## Quickstart
1. Navigate to **Smart Mining**.
2. Paste the source URL.
3. Optionally set a display name.
4. Click **Start Smart Mode**.
5. Watch status updates until records appear.
6. Review records and approve/export-ready entries.

## Recommended operator workflow
1. Start with a clean source URL homepage.
2. Wait for first records (goal: < 5 minutes).
3. Prioritize high-confidence records for approval.
4. Use provenance panel for low-confidence fields.
5. Retry failed run only after checking troubleshooting steps.

## Status meanings
- `queued`: request accepted, waiting for worker.
- `running`: crawl/extraction in progress.
- `completed`: run finished.
- `failed`: run ended with recoverable failure.

## Quality tips
- For mixed-content sites, validate first 10 records before bulk approvals.
- Use image panel to verify attribution and broken media links.
- Flag extraction anomalies early through beta feedback form.
