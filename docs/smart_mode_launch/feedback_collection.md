# Smart Mode Feedback Collection Setup

## Channels
1. **In-app post-run survey** (required)
   - CSAT score (1–5)
   - Time-to-first-record (minutes)
   - Confidence in record quality (1–5)
   - Free-text: what confused you most?
2. **Bug intake form** (required for issues)
   - Repro steps
   - Expected vs actual result
   - Severity proposal (P0/P1/P2/P3)
   - Screenshot / video link
3. **Weekly 20-minute beta sync**
   - Top friction points
   - Feature requests
   - Clarification gaps in docs

## Feedback operations cadence
- Daily triage at 16:00 UTC.
- P0 acknowledged in 15 minutes.
- P1 acknowledged within same business day.
- P2/P3 logged in post-launch backlog.

## Satisfaction target
- Launch gate requires average CSAT > 4.0/5.0.
- Any tester with score <= 2 triggers follow-up interview.

## Artifact destinations
- Survey responses: `analytics.smart_mode_beta_survey` table (or equivalent BI sink).
- Bug tickets: project board label `smart-mode-beta`.
- Weekly summary: `docs/smart_mode_launch/beta_weekly_summary.md` (append-only).
