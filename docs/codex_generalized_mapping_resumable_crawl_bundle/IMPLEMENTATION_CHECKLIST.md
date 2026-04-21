# Implementation Checklist

## Phase 1: profiler
- [ ] Create source profiling models
- [ ] Add seed URL sampler
- [ ] Add sitemap discovery
- [ ] Add nav/internal-link discovery
- [ ] Cluster URLs by path pattern
- [ ] Add representative sample selection
- [ ] Add family candidate page typing
- [ ] Add profiler API endpoint
- [ ] Add profiler tests

## Phase 2: mapping suggestion
- [ ] Add mapping suggestion model
- [ ] Generate candidate family rules
- [ ] Add pagination detection
- [ ] Add include/exclude suggestions
- [ ] Add follow policy suggestions
- [ ] Add LLM ambiguity fallback only for unclear families
- [ ] Add draft mapping save flow
- [ ] Add mapping suggestion tests

## Phase 3: admin approval UI
- [ ] Add new source onboarding wizard UI
- [ ] Add family preview cards
- [ ] Add family overrides
- [ ] Add publish mapping version action
- [ ] Add start crawl action from approved mapping
- [ ] Add UI tests if available

## Phase 4: durable frontier
- [ ] Add FrontierUrl model/table
- [ ] Add CrawlRunCheckpoint model/table
- [ ] Persist discovered URLs
- [ ] Persist status transitions
- [ ] Add retry metadata
- [ ] Add resume endpoint/service
- [ ] Ensure queue integrates with durable frontier
- [ ] Add resume tests

## Phase 5: freshness
- [ ] Add family freshness policies
- [ ] Add next_eligible_fetch_at scheduling
- [ ] Add content hash tracking
- [ ] Add targeted refresh logic
- [ ] Add freshness tests

## Phase 6: drift
- [ ] Add MappingDriftSignal model/table
- [ ] Add null-rate anomaly signal
- [ ] Add new-family detection
- [ ] Add drift API/UI surface
- [ ] Add draft remap proposal flow
- [ ] Add drift tests

## Cross-cutting
- [ ] Add docs for new source onboarding
- [ ] Add benchmark fixtures for mixed site structures
- [ ] Add observability for family decisions and skip reasons
- [ ] Add migration files
- [ ] Add manual operator smoke-test checklist
