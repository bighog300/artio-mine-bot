# Smart Mode Troubleshooting Guide

## 1) No records after 5+ minutes
**Symptoms**
- Job remains `running`
- `records_count` remains `0`

**Checks**
1. Confirm source URL is publicly reachable.
2. Verify no robots/crawl restrictions block key sections.
3. Check job status endpoint for `error/helpful_error`.

**Action**
- Retry the run.
- If repeated, file P1 ticket with source URL and timestamps.

## 2) Run failed immediately
**Symptoms**
- `job_status = failed`

**Checks**
1. Validate URL format (`https://...`).
2. Confirm source state is retryable.

**Action**
- Use retry endpoint.
- If failure recurs twice, escalate as P0 if reproducible on multiple sources.

## 3) Low-quality extracted fields
**Symptoms**
- Incorrect date/location/title fields.

**Checks**
1. Open provenance details for raw source context.
2. Compare against source page.

**Action**
- Correct record manually.
- Submit beta feedback with sample URL and expected values.

## 4) Missing images or broken thumbnails
**Symptoms**
- image preview unavailable

**Checks**
1. Open image URL directly.
2. Confirm image host allows hotlinking/CORS.

**Action**
- Replace with alternate valid image URL where possible.
- Log as P2 if non-blocking.

## 5) Permission error on metrics endpoint
**Symptoms**
- 403 response from `/smart-mine/metrics`

**Action**
- Use admin account or request admin role assignment.
