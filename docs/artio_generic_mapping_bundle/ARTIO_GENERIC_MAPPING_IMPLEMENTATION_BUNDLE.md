# Artio Mine Bot — Generic Mapping-Driven Extraction Implementation Bundle

## Goal

Refactor the platform so it is **source-agnostic by default** and becomes domain-specific **only through the mapping workflow**.

The desired product behavior is:

1. User enters a source URL.
2. System scans the source generically for structure and content.
3. AI proposes site structure, page clusters, selectors, follow rules, and candidate record mappings.
4. Admin reviews and approves or edits the mapping.
5. Approved mapping becomes the runtime extraction contract.
6. Mining runs deterministically from the approved mapping and produces records such as artists, venues, events, exhibitions, artworks, and future record types.

## Core Design Principle

The system should be:

- **generic in discovery**
- **configurable in mapping**
- **deterministic in mining**

## Problem Statement

The current codebase still contains remnants of an art-site-specific design, especially around page inference, crawling assumptions, and extraction terminology.

That creates three problems:

1. **Discovery is not fully generic**
   - generic scanning layers still contain domain/path assumptions
   - some code paths appear to rely on art.co.za-specific URL or page-role inference

2. **Mapping is not yet the sole source of truth**
   - mining can still depend on hardcoded source-specific logic
   - art-specific page type names bleed into runtime behavior

3. **Record targeting is too tightly coupled to source assumptions**
   - page roles and target entities are not cleanly separated
   - the system should infer structure first, then let the admin decide whether a page cluster maps to artist, venue, event, etc.

## Desired Target Model

### Stage 1 — Source ingestion
The user submits a source URL.

Store:
- source URL
- scan options
- source status

### Stage 2 — Generic site scan
The crawler and AI should discover:
- representative pages
- URL clusters
- repeated DOM/layout structures
- listing/detail/directory patterns
- pagination and follow-link opportunities
- candidate fields and content blocks

The scan phase should **not assume art-specific semantics**.

### Stage 3 — Mapping proposal
The proposal system should produce:
- generic page-role proposals
- candidate selectors
- candidate fields
- candidate target record types
- follow rules
- confidence scores

The page-role proposal should be generic first.

Examples of generic page roles:
- `detail_page`
- `listing_page`
- `directory_page`
- `profile_page`
- `event_page`
- `location_page`
- `category_page`
- `index_page`

Then the reviewer can assign target record types.

### Stage 4 — Mapping approval
The admin must be able to:
- approve/reject clusters or rows
- rename or refine page groups
- choose target record type (`artist`, `venue`, `event`, etc.)
- edit selectors
- edit field mappings
- define follow rules
- define required fields

This is where domain specificity enters.

### Stage 5 — Runtime map generation
The approved mapping should generate a runtime map containing:
- crawl plan
- page classification rules
- extraction rules
- record target mappings
- normalization rules

This runtime map should be sufficient for mining without any source-specific hardcoded path inference.

### Stage 6 — Mining
Mining should execute from the runtime map only.

The mining engine should not require:
- `if domain == art.co.za`
- path-specific artist slug inference
- hardcoded art section assumptions

Optional source-specific heuristics can exist only as non-blocking hints or plugins, not the main path.

### Stage 7 — Record review
Extracted records should flow into moderation queues by target record type, such as:
- artist
- venue
- event
- exhibition
- artwork
- future schemas

## Architectural Changes Required

## 1. Make discovery generic

### Objective
Ensure scanning and clustering work for any source URL, not just art-specific sites.

### Files to inspect
- `app/source_mapper/service.py`
- `app/source_mapper/page_clustering.py`
- `app/source_mapper/proposal_engine.py`
- `app/crawler/automated_crawler.py`
- `app/crawler/durable_frontier.py`
- `app/pipeline/runner.py`

### Required changes
- Remove or isolate art-specific assumptions from generic discovery and scan logic.
- Audit for any of the following in generic code paths:
  - `/artists/`
  - artist slug assumptions
  - art.co.za-specific path filters
  - hardcoded page-role inference tied to one domain
- Keep source-specific logic only as optional heuristics, not required runtime behavior.
- Ensure generic discovery produces clusters and field candidates without domain-specific assumptions.

### Acceptance criteria
- A non-art source can be scanned without requiring art-specific inference.
- Generic discovery layers do not silently discard useful pages due to art-specific path filtering.

## 2. Separate generic page roles from target record types

### Objective
Stop conflating structural page type with business entity type.

### Files to inspect
- `app/source_mapper/proposal_engine.py`
- `app/source_mapper/service.py`
- `app/db/crud.py`
- mapping-related frontend types/components
- any runtime-map builders

### Required changes
Introduce or normalize a two-layer model:

1. **page role / page cluster type**
   - generic structural meaning
   - examples: `detail_page`, `listing_page`, `directory_page`, `profile_page`, `event_page`, `location_page`

2. **target record type**
   - business entity to create
   - examples: `artist`, `venue`, `event`, `exhibition`, `artwork`

Update mapping rows / preset rows / runtime-map generation so a row can express both:
- structural page role
- target record type

Do not require target record type to be fixed by the scanner.

### Acceptance criteria
- A discovered page cluster can be assigned to different target entity types during mapping review.
- Proposal code no longer hardcodes art-specific page type names as the only canonical path.

## 3. Make mapping the authoritative intelligence layer

### Objective
After mapping approval, the runtime map must be sufficient to drive mining.

### Files to inspect
- `app/db/crud.py`
- `app/pipeline/runner.py`
- `app/crawler/automated_crawler.py`
- `app/api/routes/mine.py`

### Required changes
- Ensure approved mapping produces a complete runtime map.
- Runtime map should include enough classification/extraction information to avoid hardcoded source-specific logic.
- If classification currently depends on domain-specific inference, replace or demote it behind mapping-driven rules.
- Treat source-specific inference as fallback only, not the normal path.

Potential runtime-map areas to strengthen:
- page classification identifiers/patterns
- extraction rules
- target record mappings
- follow rules
- normalization instructions

### Acceptance criteria
- A source with an approved runtime map can be mined without depending on art.co.za-specific URL inference.
- Mining from approved mapping works for multiple record types on the same source.

## 4. Add explicit target record type mapping in the admin workflow

### Objective
Make the mapping UI the place where domain specificity is chosen.

### Files to inspect
- `frontend/src/pages/SourceMapping.tsx`
- `frontend/src/components/source-mapper/*`
- `frontend/src/lib/api.ts`
- source-mapper backend routes and schemas

### Required changes
Allow mapping review to explicitly choose a target record type for a page group or mapping row.

At minimum support:
- `artist`
- `venue`
- `event`

Prefer designing for extension to:
- `exhibition`
- `artwork`
- `organization`
- future record schemas

The UI should let the reviewer see:
- discovered cluster/page role
- proposed selectors
- proposed fields
- target record type
- confidence

### Acceptance criteria
- An admin can map one cluster to artists, another to venues, another to events.
- The approved mapping clearly encodes target record type.

## 5. Make proposal generation schema-aware, not site-aware

### Objective
The proposal engine should know about possible record schemas, not specific sites.

### Files to inspect
- `app/source_mapper/proposal_engine.py`
- any AI prompting / proposal generation helpers
- mapping row schemas

### Required changes
- Replace art-site-specific assumptions with schema-aware proposal generation.
- AI should propose candidates like:
  - “this page likely matches venue schema”
  - “this page likely matches event schema”
  - “this page likely matches artist schema”
- Keep proposals probabilistic and reviewable, not authoritative.

If the current system already has destination categories, evolve them toward a cleaner record-schema model.

### Acceptance criteria
- Proposal generation can suggest multiple candidate record types from page content.
- Proposal generation does not assume the source is an art site.

## 6. Strengthen runtime map semantics for multi-entity extraction

### Objective
Support sources that contain multiple entity families.

### Files to inspect
- `app/db/crud.py`
- runtime-map generation code
- mining/extraction code paths
- records ingestion/persistence code

### Required changes
Ensure the runtime map can represent multiple approved entity families for one source.

For example:
- cluster A → target `artist`
- cluster B → target `venue`
- cluster C → target `event`

The mining engine must preserve target type through extraction and persistence.

### Acceptance criteria
- A single source can produce artists, venues, and events from separate approved page groups.
- Records enter the correct moderation queue/type.

## 7. Demote source-specific heuristics into optional plugins or fallbacks

### Objective
Keep useful heuristics without letting them define the architecture.

### Files to inspect
- `app/pipeline/runner.py`
- `app/source_mapper/service.py`
- `app/crawler/automated_crawler.py`

### Required changes
- Audit art.co.za-specific logic such as path-based role inference or ignore rules.
- If these are still useful, isolate them behind an optional heuristic layer.
- They must not be required for successful operation when a runtime map exists.

### Acceptance criteria
- The main success path is mapping-driven, not source-heuristic-driven.
- Heuristics can assist discovery but do not block generic sources.

## 8. Update records moderation to reflect mapping-defined target types

### Objective
Ensure the records system aligns with mapping-defined entities.

### Files to inspect
- `frontend/src/pages/Records.tsx`
- `frontend/src/pages/RecordDetail.tsx`
- `app/api/routes/records.py`
- record CRUD/model layers

### Required changes
- Ensure extracted records carry the target record type defined by mapping.
- Records UI should remain able to browse/filter/moderate by type.
- Approve/reject/edit flows must continue to work for artists, venues, events, and future target types.

### Acceptance criteria
- Moderation queue supports records from multiple target types generated from mapping.
- No code path assumes only artist-like records matter.

## 9. Improve source mapping UX around cluster-to-record assignment

### Objective
Make the UI reflect the generic-to-specific mapping process.

### Files to inspect
- `frontend/src/pages/SourceMapping.tsx`
- `frontend/src/components/source-mapper/*`

### Required changes
Add or improve UI elements for:
- generic page-role display
- target record type selection
- candidate fields by record type
- clear “next step” guidance

The reviewer experience should become:
- inspect cluster
- choose target record type
- refine selectors/fields
- approve mapping

### Acceptance criteria
- The page clearly communicates that domain specificity is chosen during mapping review.
- The workflow is understandable for non-art sources.

## Phased Implementation Plan

### Phase 1 — Runtime and architecture hardening
- remove hard dependency on art-specific inference in mining success path
- strengthen runtime-map generation and classification
- preserve current working behavior with backward compatibility where practical

### Phase 2 — Generic proposal + mapping model
- introduce clearer separation between page role and target record type
- update proposal and mapping schemas

### Phase 3 — Admin workflow updates
- expose target record assignment and generic workflow semantics in Source Mapping UI

### Phase 4 — Multi-entity extraction validation
- validate that a single source can generate artists, venues, and events through mapping

## Testing Requirements

Add or update tests to cover:

### Backend
- generic runtime-map classification independent of art-specific domain inference
- sources with multiple record targets in one runtime map
- proposal/runtime-map generation that includes target record types
- mining success when mapping exists but source-specific heuristics are absent
- non-art source scan/mapping smoke coverage where practical

### Frontend
- Source Mapping UI supports assigning target record types
- workflow guidance reflects generic mapping model
- records browsing/moderation works for multiple target types

Run and report:
- relevant `pytest` suites
- relevant frontend tests
- `npm -C frontend run build`

## Constraints

- Make focused, incremental changes
- Preserve existing working flows where possible
- Do not add migrations unless absolutely necessary
- Do not do a speculative rewrite of the entire pipeline
- Prefer compatibility shims where old art-specific terms still exist but must be phased out
- Be explicit when a change is transitional vs. final architecture

## Deliverables

After implementation, provide:

1. **Root causes addressed**
   - where art-specific assumptions were still embedded
   - where mapping was not yet authoritative

2. **Files changed**
   - every file edited
   - one-line purpose for each

3. **Tests run and outcomes**
   - exact commands
   - pass/fail results

4. **Remaining risks / follow-up**
   - especially any remaining art-specific heuristic paths
   - any schema/generalization work left for future phases

## Definition of Done

This bundle is complete when:
- the platform can ingest a generic source URL,
- scanning and AI proposal are structurally generic,
- domain/entity specificity is chosen in the mapping workflow,
- approved mapping drives mining without requiring art-site-specific hardcoding,
- one source can produce multiple record types like artist, venue, and event,
- records moderation still works on the resulting entities.
