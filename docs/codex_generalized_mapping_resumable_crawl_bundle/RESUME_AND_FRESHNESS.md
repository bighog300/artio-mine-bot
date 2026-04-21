# Resume and Freshness Strategy

## Resume model

A crawl should never depend only on in-memory queue state.

Persist:
- discovered URLs
- pending URLs
- active URLs
- failed URLs
- completion status
- last processed URL
- mapping version used

A resume operation should:
- reload pending/retryable frontier items
- continue with the same mapping version unless explicitly upgraded
- preserve diagnostics and retry history

## Frontier lifecycle

Recommended statuses:
- discovered
- queued
- fetching
- fetched
- extracted
- skipped
- failed_retryable
- failed_terminal

## Refresh model

Each family should have a freshness policy:
- realtime-ish
- daily
- weekly
- monthly
- archive/manual

Use:
- `next_eligible_fetch_at`
- `content_hash`
- `etag`
- `last_modified`
- family-specific priority

## Change detection

Trigger re-extract or recrawl when:
- content hash changes
- key structured markers disappear
- canonical URL changes
- page-family assignment changes
- operator requests targeted refresh

## Resume from same crawl location

This should mean:
- continue from persistent frontier state
- not “start at the original URL again and rediscover everything”

Checkpoint fields should be enough to:
- restore progress
- show where the run paused
- continue safely
