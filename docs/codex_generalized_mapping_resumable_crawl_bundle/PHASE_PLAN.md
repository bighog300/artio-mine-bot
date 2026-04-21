# Phase Plan

## Phase 1: Site profiler and URL family clustering
Build a source profiling layer that can inspect a seed URL and produce:
- site fingerprint
- discovered entrypoints
- URL family clusters
- representative pages per cluster
- candidate page types with confidence

### Deliverables
- seed URL sampler
- sitemap/navigation discovery
- URL clustering by path pattern
- DOM similarity / structural grouping
- page-family summaries
- candidate crawl strategy suggestions

### Success criteria
- the system can profile a previously unseen site
- the admin can see grouped URL families with samples
- obvious site families such as artists/exhibitions/artworks/listings are surfaced

---

## Phase 2: Mapping suggestion engine
Build a hybrid suggestion engine that proposes crawl/mapping options from profiler output.

### Deliverables
- page-family typing
- candidate mapping presets
- follow-link policies
- pagination detection
- include/exclude suggestions
- heuristic-first + LLM-assisted ambiguity resolution

### Success criteria
- the system produces at least one workable mapping option for varied site structures
- suggested mappings are previewable and editable
- admin can approve one mapping version for execution

---

## Phase 3: Admin approval workflow
Build an operator workflow to review and approve mappings.

### Deliverables
- onboarding wizard for a new source URL
- family preview cards
- sample extraction preview
- include/exclude toggles
- page type overrides
- mapping version save/publish action

### Success criteria
- an operator can onboard a new source without editing code
- the approved mapping is stored and versioned
- crawl execution can start directly from approved mapping

---

## Phase 4: Durable frontier and resumable crawling
Build crawl persistence so runs can resume from the same location instead of restarting.

### Deliverables
- persistent frontier table
- per-URL status tracking
- checkpointed crawl runs
- retry and backoff metadata
- resume-from-pending support
- page hash / change tracking

### Success criteria
- interrupted crawls can be resumed
- duplicate work is minimized
- crawl runs have visible progress and state transitions

---

## Phase 5: Incremental freshness recrawls
Keep mining fresh without recrawling everything.

### Deliverables
- next-eligible-fetch scheduling
- page-family freshness policies
- change detection using content hash / etag / modified date where possible
- targeted reextract / recrawl

### Success criteria
- high-value or fresh page families are revisited more often
- stable archive content is revisited less frequently
- the system can run refresh crawls efficiently

---

## Phase 6: Drift detection and mapping versioning
Detect when mappings go stale and propose refreshes.

### Deliverables
- mapping version model
- extraction degradation signals
- null-rate anomaly detection
- new URL family detection
- remap suggestion queue

### Success criteria
- the system can detect site structure drift
- operators are alerted with actionable mapping update proposals
- old runs remain attributable to the mapping version used
