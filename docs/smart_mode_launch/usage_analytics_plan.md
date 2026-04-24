# Smart Mode Usage Analytics Monitoring Plan

## Core launch metrics
1. **Beta completion rate** = testers who finish script / total testers.
2. **Median time-to-first-record** from mining start to first persisted record.
3. **Smart Mode success rate** = successful runs / total runs.
4. **Average CSAT** from post-run survey.

## Required events
- `smart_mode_started`
- `smart_mode_progress_heartbeat`
- `smart_mode_first_record_created`
- `smart_mode_completed`
- `smart_mode_failed`
- `record_review_action`
- `beta_feedback_submitted`

## Dashboard slices
- By tester account
- By source type (gallery, museum, venue, blog)
- By failure class (crawl, extraction, API, validation)
- By runtime bucket (0-5m, 5-10m, >10m)

## Alert thresholds
- Success rate < 85% in trailing 24h -> page launch owner.
- Median time-to-first-record >= 5 min in trailing 24h -> investigate crawl/extract bottlenecks.
- CSAT <= 4.0 average after first 5 tester sessions -> trigger docs+UX review.

## Daily launch report template
- Date window (UTC)
- Testers active / completed
- Success rate and top 3 failure reasons
- Time-to-first-record p50 / p95
- CSAT average and notable comments
- Open P0 / P1 count
