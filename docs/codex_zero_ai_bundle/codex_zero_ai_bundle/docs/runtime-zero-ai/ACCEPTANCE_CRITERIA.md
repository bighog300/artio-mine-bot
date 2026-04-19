# Acceptance criteria

## Functional

### AC1 — Discovery can generate a runtime mapping
Given a new source,
when a discovery run completes,
then the system stores a draft mapping version containing crawl targets, page types, extraction rules, and follow rules.

### AC2 — A mapping can be published
Given a source with a draft mapping version,
when that mapping is published,
then the source references the published mapping version as its active runtime contract.

### AC3 — Published runtime crawl uses zero AI
Given a source with a published runtime mapping,
when a normal crawl/mining job runs,
then no OpenAI client calls occur anywhere in the runtime execution path.

### AC4 — Runtime extraction is deterministic
Given a published source and a matching page,
when the page is processed,
then classification and extraction use only URL rules, selectors, regex, and deterministic normalization logic.

### AC5 — Unknown or low-confidence pages are queued for review
Given a published source and a page that cannot be classified or deterministically extracted,
when runtime processes the page,
then the page is marked with a review reason and runtime does not call AI.

### AC6 — Unchanged pages are skipped
Given a page whose content hash is unchanged and whose mapping version is unchanged,
when runtime reprocesses the source,
then the page is skipped without re-extraction.

### AC7 — Drift is surfaced
Given repeated selector misses or degraded extraction hit rates,
when thresholds are exceeded,
then the source is marked `mapping_stale` and runtime still does not call AI.

## Observability

### AC8 — Runtime logs prove policy
Runtime logs include structured fields indicating:
- job type
- source runtime mode
- AI policy state
- whether a page was extracted, skipped, or queued for review

### AC9 — Token accounting is separated
The system can distinguish discovery AI token usage from runtime AI token usage, and runtime usage remains zero for published-source jobs.

## Safety

### AC10 — Runtime fails closed
If a published-source runtime job accidentally reaches an AI path,
then the system blocks the call and records a deterministic failure/review outcome rather than silently spending tokens.

## Suggested verification checklist

- run tests for mapping lifecycle
- run a discovery flow on a fixture source
- publish mapping
- run runtime crawl with AI client mocked/spied
- assert zero AI calls
- assert extracted pages persist successfully
- assert unsupported pages are marked for review
- assert unchanged pages are skipped on second run
