# Operator Notes — Durable Crawl Runs

New crawl-run APIs:

- `GET /api/sources/{source_id}/crawl-runs`
- `GET /api/crawl-runs/{crawl_run_id}`
- `GET /api/crawl-runs/{crawl_run_id}/frontier`
- `GET /api/crawl-runs/{crawl_run_id}/pages`
- `GET /api/crawl-runs/{crawl_run_id}/records`
- `POST /api/crawl-runs/{crawl_run_id}/pause`
- `POST /api/crawl-runs/{crawl_run_id}/resume`
- `POST /api/crawl-runs/{crawl_run_id}/cancel`
- `POST /api/crawl-runs/{crawl_run_id}/reclaim-stale`
- `GET /api/crawl-runs/{crawl_run_id}/stream` (SSE)
- `GET /api/jobs/{job_id}/stream` (SSE)

Behavior:

- Crawl ingestion persists frontier rows in `crawl_frontier`; leases are reclaimed automatically when expired.
- Rate-limited rows are persisted with `next_retry_at` and reflected as `rate_limited`.
- Source and crawl-run pause/resume controls both gate leasing.
- Pages appear as soon as crawl ingestion stores them; enrichment remains separately triggerable via existing extraction endpoints.
