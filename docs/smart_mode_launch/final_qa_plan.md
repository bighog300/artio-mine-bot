# Smart Mode Final QA Plan

## 1) User flow validation
- URL submission and source creation
- Smart Mode run kickoff
- Live status tracking
- Record review actions (approve/reject/edit)
- Export-ready marking

**Exit criteria**
- 100% pass for core path on staging and production-like environment.

## 2) Error scenario validation
- Invalid URL input
- Source not found (status/retry)
- Retry on non-retryable state (expect 422)
- Metrics access with non-admin account (expect 403)
- Upstream AI/crawl transient failures with helpful error text

**Exit criteria**
- All expected errors are actionable and non-destructive.

## 3) Performance validation
- Time-to-first-record p50 < 5 minutes.
- Success rate > 85% across beta cohort.
- Status endpoint remains responsive under concurrent runs.

**Exit criteria**
- Performance metrics meet launch thresholds for 3 consecutive days.

## 4) Security review
- Verify admin-only metrics endpoint enforcement.
- Confirm API keys/tokens are never exposed in UI logs.
- Validate audit logging on critical actions.
- Ensure rate-limiting and auth middleware applied to Smart Mode routes.

**Exit criteria**
- No open high-severity security findings.

## Launch gate checklist
- [ ] 10/10 beta testers complete script.
- [ ] Average CSAT > 4.0.
- [ ] Median time-to-first-record < 5 min.
- [ ] Smart Mode success rate > 85%.
- [ ] Zero open P0 issues.
- [ ] Zero open critical P1 issues.
