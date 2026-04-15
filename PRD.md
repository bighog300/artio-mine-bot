# AI Source Mapper — Product Requirements Document

## 1. Summary

Add an admin-facing **AI Source Mapper** that allows an operator to enter a source URL, run an AI-assisted site scan, see AI-proposed mappings in a moderation-friendly matrix, preview how extracted values will be stored and categorized, edit mappings easily, and publish a source mapping set for production mining.

This extends the current source creation and crawl setup flow from a technical configuration form into a guided, preview-first extraction design workflow.

## 2. Problem

The current repo supports sources, crawl intent, extraction rules, and mining jobs, but the setup process still assumes a relatively technical operator. The missing layer is a guided structure-mapping workflow that:

- discovers page templates automatically
- proposes extraction mappings visually
- lets admins correct mappings before ingesting data at scale
- shows exactly where extracted data will land in the existing record schema
- supports moderation, approval, and rollback

Without this layer, admins are more likely to:

- configure the wrong crawl strategy
- over-crawl irrelevant pages
- map content to the wrong record type or field
- import low-quality or mis-categorized data
- rely on trial-and-error instead of preview and approval

## 3. Goals

### Primary goals

- Allow admins to enter a source URL and get an AI-generated site mapping proposal.
- Display proposed mappings in an **admin matrix panel**.
- Make mappings easy to edit and moderate.
- Provide a preview showing extracted source data and destination storage/category before publish.
- Support safe approval for sample pages before full ingestion.

### Secondary goals

- Reuse existing source, page, record, and mining flows where possible.
- Keep the feature compatible with the current record schema.
- Build in versioning so future rescans do not overwrite approved mappings silently.
- Lay groundwork for later self-improving mapping suggestions using admin feedback.

## 4. Non-goals for initial MVP

- No fully autonomous, self-publishing import rules.
- No arbitrary end-user custom schemas in v1.
- No broad WYSIWYG scraping IDE.
- No requirement to support every edge-case site structure in v1.
- No continuous learning pipeline that mutates published mappings automatically.

## 5. Users

### Primary user
Operations/admin user who manages source onboarding and data quality.

### Secondary user
Technical operator who debugs site extraction quality and adjusts mappings.

## 6. Core user stories

### Source setup
- As an admin, I can paste a site URL and request a scan.
- As an admin, I can constrain the scan by path, depth, or page count.
- As an admin, I can see which page types the AI thinks exist on the site.

### Mapping review
- As an admin, I can view AI-proposed mappings in a matrix.
- As an admin, I can approve, reject, disable, or edit any mapping.
- As an admin, I can change the destination entity and field inline.
- As an admin, I can drag a source field onto a destination schema field.

### Preview
- As an admin, I can inspect a live preview for a sample page.
- As an admin, I can see the source snippet, extracted value, destination field, and category.
- As an admin, I can confirm what will be stored before the mapping is published.

### Publish and safety
- As an admin, I can publish a mapping version only after reviewing sample output.
- As an admin, I can roll back to a previous mapping version.
- As an admin, I can rescan a site without losing my published mapping until I explicitly replace it.

## 7. Proposed workflow

### Step 1 — Create mapping draft
Admin enters:
- source URL
- optional source name
- crawl scope
- allowed paths / blocked paths
- max pages
- max depth

### Step 2 — AI scan
System performs:
- URL normalization
- page sampling / crawl discovery
- page template clustering
- structured data detection
- repeated block detection
- field candidate extraction
- destination schema suggestion
- taxonomy/category suggestion

### Step 3 — Review matrix
System presents a matrix with rows like:
- page type
- source selector/pattern
- sample value
- extracted field label
- destination entity
- destination field
- category/taxonomy target
- confidence
- status

### Step 4 — Preview
Admin opens a preview showing:
- rendered source sample
- highlighted extraction regions
- proposed destination record preview
- category placement preview

### Step 5 — Approve sample run
Admin reviews 5–20 sample pages and:
- approves
- edits
- rejects
- marks rule to ignore

### Step 6 — Publish
Admin publishes the draft mapping version.
Future mining jobs use the published mapping set.

## 8. Functional requirements

### 8.1 Site scan and page-type detection
The system must:
- accept a source URL and scan options
- discover sample pages from the site
- identify likely page types such as listing, artist, event, venue, article, image gallery
- group similar pages into page-type clusters
- show confidence levels for page-type classification

### 8.2 Mapping proposal generation
The system must propose mappings for:
- title-like fields
- description-like fields
- dates and times
- venue/location fields
- artist/person names
- media/image blocks
- taxonomy/tag/category fields
- links such as ticket URLs and website URLs

The proposal should include:
- source pattern or selector
- sample extracted values
- likely destination entity and field
- optional category/taxonomy recommendation
- confidence score and rationale

### 8.3 Admin matrix panel
The matrix must support:
- sortable columns
- filtering by page type, status, confidence, destination entity
- inline editing of mapping rows
- bulk approve/reject
- mark as required / optional
- enable / disable mapping
- duplicate/conflict highlighting

### 8.4 Drag-and-drop moderation
The UI should support:
- dragging a source field row onto a destination schema field
- changing destination entity by drag-and-drop
- reordering field priority
- moving uncategorized fields into target buckets

MVP may ship inline editing first and add drag-and-drop in phase 2.

### 8.5 Preview and confirmation
Preview must show:
- sample page URL
- source snippet or highlighted DOM region
- extracted value
- destination entity
- destination field
- category/taxonomy result
- transformed output preview if normalization applies

### 8.6 Mapping lifecycle and moderation
Mappings must support:
- draft state
- published state
- archived state
- version history
- change audit trail
- publish timestamp and actor
- rollback to previous version

### 8.7 Safe sample run
Before full ingestion, admins must be able to run sample extraction against a small set of pages and review generated output.

## 9. Quality requirements

- Scan response must degrade gracefully if some pages fail to fetch.
- AI confidence must never replace admin approval.
- Optional preview data should not create production records.
- Published mappings must be immutable; edits create a new draft version.
- Every mapping change must be attributable to a user and timestamp.

## 10. Success metrics

- Reduced time to configure a new source
- Reduced mapping correction rate after first publish
- Higher approval rate on first sample run
- Lower operator support burden for source onboarding
- Lower record rejection rate after mapping-guided onboarding

## 11. Acceptance criteria

- Admin can create a mapping draft from a source URL.
- AI scan returns page types and proposed mappings.
- Admin can edit mappings in a matrix.
- Admin can preview extracted values and destination storage before publish.
- Admin can approve a sample set and publish a mapping version.
- Published mappings are versioned and rollback-capable.
