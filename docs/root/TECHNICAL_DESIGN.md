# AI Source Mapper — Technical Design

## 1. Overview

The feature should be implemented as a **mapping draft pipeline** layered on top of the existing source and mining architecture.

High-level flow:

1. Create or select source
2. Start a scan job
3. Crawl/sample pages for discovery
4. Cluster pages into page types
5. Generate mapping proposals
6. Persist draft mapping set + rows + samples
7. Support preview and sample extraction
8. Publish mapping version
9. Mining pipeline consumes published mapping version

## 2. Existing repo integration points

### Existing backend areas to extend
- `app/api/routes/sources.py`
- `app/api/routes/mine.py`
- `app/api/schemas.py`
- `app/db/models.py`
- `app/db/crud.py`
- `app/crawler/*`
- `app/extraction/*`
- `app/queue.py`

### Existing frontend areas to extend
- `frontend/src/lib/api.ts`
- `frontend/src/pages/Sources.tsx`
- `frontend/src/pages/SourceDetail.tsx`
- `frontend/src/App.tsx`

## 3. Proposed architecture

### 3.1 New backend concepts

#### Source scan job
Discovers page samples, candidate templates, repeated blocks, and structured data.

#### Mapping proposal generator
Transforms discovered page signals into proposed mappings.

#### Mapping preview generator
Runs proposed mappings against sample pages and produces a destination record preview.

#### Mapping version publisher
Copies approved draft mappings into a published version used by mining.

## 4. Processing stages

### Stage A — Discovery scan
Inputs:
- source URL
- scan options
- path allow/block rules

Outputs:
- sampled pages
- page clusters
- page type suggestions
- candidate selectors / extraction patterns

### Stage B — Proposal generation
Inputs:
- sampled pages
- cluster summaries
- DOM/structured data analysis
- AI classifier/extractor

Outputs:
- mapping draft version
- mapping rows
- confidence values
- sample values

### Stage C — Preview generation
Inputs:
- mapping rows
- sample page

Outputs:
- extracted field values
- normalized values
- destination entity preview
- category/taxonomy preview

### Stage D — Publish
Inputs:
- approved mapping draft

Outputs:
- published version
- source references published mapping version
- audit log entry

## 5. Data flow into mining pipeline

When a source has a published mapping version:
- mining should prefer explicit published mapping rules over ad hoc extraction hints
- extraction pipeline should load the latest published mapping version by source
- preview/sample-only records must not be written as production `records`

## 6. New backend modules recommended

- `app/api/routes/source_mapper.py`
- `app/source_mapper/service.py`
- `app/source_mapper/proposal_engine.py`
- `app/source_mapper/preview.py`
- `app/source_mapper/page_clustering.py`
- `app/source_mapper/types.py`

These can start simple and call existing crawler/extraction utilities.

## 7. Source scan strategy

### MVP
- fetch source URL
- inspect sitemap if available
- sample internal links
- classify pages into rough clusters using URL patterns, titles, DOM structure, and repeated block analysis
- capture representative HTML snippets for preview

### Later improvements
- visual similarity clustering
- selector stability scoring across multiple pages
- diffing across rescans

## 8. Mapping rule representation

Each mapping row should represent a single source-to-destination proposal.

Suggested attributes:
- page type key
- source selector or structural pattern
- extraction mode (`text`, `html`, `attr`, `jsonld`, `meta`, `regex`, `llm`)
- destination entity
- destination field
- category target
- transform chain
- confidence
- status
- rationale
- sample value

## 9. Publish and versioning model

Use immutable versions.

Rules:
- draft versions are editable
- published versions are immutable
- editing a published version creates a new draft
- one source can have one active published version
- source references `active_mapping_version_id`

## 10. Preview implementation notes

Preview should be computed from stored sample pages or page snapshots.

Do not:
- write preview results into production records
- mutate published mappings during preview

Do:
- compute normalized values
- show exact destination paths
- show category assignment
- show validation warnings

## 11. Frontend design notes

### Route plan
- keep `Sources` as entry point
- add `Source Mapping` route/tab
- surface scan state and publish state in `SourceDetail`

### State management
Use React Query for:
- scan status
- mapping versions
- mapping rows
- preview results
- sample extraction results

Keep local component state for:
- unsaved edits
- drag-and-drop state
- column filters
- selection / bulk actions

## 12. Permissions and audit

The repo already uses `require_permission` in routes.
Recommended permissions:
- read mapping drafts: `read`
- edit drafts / run scans / publish: `write`
- rollback or delete versions: `write` or future `admin`

Every publish or rollback should create an audit log row.

## 13. Operational safety

- cap page scan depth/pages in MVP
- add timeout handling around scans
- return partial results when some samples fail
- prevent duplicate scan jobs per source unless explicitly retried
- show health state in UI if scan generation fails
