# Test Plan

## Unit tests

### Profiler
- sitemap discovery on site with sitemap
- fallback nav discovery when no sitemap
- URL path clustering
- representative sample selection
- page-type candidate inference for obvious families

### Mapping suggestion
- listing family gets listing-like rule suggestion
- detail family gets detail-like rule suggestion
- pagination detected from repeated page links
- include/exclude suggestions for obvious utility pages
- ambiguity falls back to LLM helper only when needed

### Frontier/resume
- discovered URLs persist
- status transitions persist
- checkpoint persists
- resume continues pending URLs
- failed_retryable URLs can be retried
- restart does not duplicate completed work

### Freshness
- high-priority families get earlier next_eligible_fetch_at
- unchanged pages skip unnecessary downstream work
- changed content triggers reextract

### Drift
- null-rate spike creates signal
- new uncovered family creates signal
- active mapping remains unchanged until admin approval of new version

## Integration tests
- profile new source -> generate mapping -> approve -> start crawl
- interrupt run -> resume -> complete
- refresh crawl after content hash change
- drift signal created after simulated site change

## Manual smoke tests
- onboard a new source with unknown structure
- review proposed families
- approve mapping
- start crawl
- pause/interruption
- resume from checkpoint
- view drift signals after mock structure change
