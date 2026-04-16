# AI Source Mapper — UX and Admin Workflows

## 1. Information architecture

Add a new source onboarding workflow centered around a mapping draft.

### New areas
- `Sources` page: entry point to launch mapping setup
- `SourceDetail` page: add a `mapping` tab
- New dedicated route: `/sources/:id/mapping`

### Recommended navigation
1. Sources list
2. Create source or open source
3. Run scan
4. Review page types
5. Review mapping matrix
6. Open preview drawer/modal
7. Run sample extraction
8. Publish mapping version

## 2. Screen inventory

### 2.1 Source Scan Setup
Purpose: collect scan input and start AI scan.

Fields:
- source URL
- source name
- allowed paths
- blocked paths
- max pages
- max depth
- page sample count
- scan mode: quick / standard / deep

Actions:
- Save draft source
- Save and scan
- Cancel

Secondary panel:
- normalized URL preview
- source duplicate warning
- crawl estimate
- robots / sitemap hints if available

## 3. Mapping Workspace layout

Use a three-pane workspace.

### Left pane — Page types and samples
- page type list
- page counts
- confidence indicator
- sample URLs
- toggle between detected templates

### Center pane — Mapping matrix
Columns:
- status
- page type
- extracted field label
- source selector / pattern
- sample value
- destination entity
- destination field
- category / taxonomy
- confidence
- actions

Actions per row:
- approve
- reject
- disable
- preview
- duplicate row
- edit

### Right pane — Schema board / preview
Tabs:
- schema board
- record preview
- category preview
- notes / rationale

The schema board should show buckets for:
- Artist
- Event
- Exhibition
- Venue
- Artwork
- Article / Other (optional, future)
- Tags / Genres / Categories
- Images / Media

## 4. Drag-and-drop behavior

### Supported interactions
- drag source field row onto destination field target
- drag row between destination entities
- drag to `Ignored` bucket
- drag to reorder priority for multi-candidate fields

### UX rules
- dropping onto a destination field updates entity + field
- dropping onto an entity bucket prompts field selection if ambiguous
- conflicts are highlighted immediately
- unsaved changes stay local until explicit save

## 5. Preview behavior

The preview must answer one question clearly:
**What will this data become if I publish this mapping?**

### Preview layout
Left:
- rendered page or HTML snapshot
- highlighted source regions

Middle:
- extracted raw values
- normalized/transformed values
- confidence and rationale

Right:
- destination record preview
- category/taxonomy preview
- storage target summary

### Preview controls
- switch sample page
- switch page type
- compare raw vs normalized
- accept / reject / edit selector

## 6. Admin moderation states

For each mapping row:
- proposed
- approved
- rejected
- ignored
- needs_review
- changed_from_published

## 7. Sample extraction review UX

Use a compact queue similar to current record review flows.

Each sample item should show:
- page URL
- page type
- generated destination entity
- field completeness
- category placement
- diff vs expected / previous mapping if applicable

Actions:
- approve sample
- reject sample
- edit mapping from sample
- flag field conflict
- mark selector unstable

## 8. Versioning UX

Published mappings must not be edited directly.

Flow:
- click `Edit published mapping`
- system clones current published version into a draft
- admin edits draft
- preview changes against sample pages
- publish new version

Include:
- version label
- created by
- published by
- published at
- rollback action

## 9. Minimum usability requirements

- matrix remains usable without drag-and-drop
- keyboard-editable controls for all critical actions
- destructive actions require confirmation
- preview never mutates production data
- bulk actions must show how many rows will change

## 10. Recommended frontend files

### Pages
- `frontend/src/pages/Sources.tsx`
- `frontend/src/pages/SourceDetail.tsx`
- new `frontend/src/pages/SourceMapping.tsx`

### Components
- `frontend/src/components/source-mapper/ScanSetupForm.tsx`
- `frontend/src/components/source-mapper/PageTypeSidebar.tsx`
- `frontend/src/components/source-mapper/MappingMatrix.tsx`
- `frontend/src/components/source-mapper/MappingRowEditor.tsx`
- `frontend/src/components/source-mapper/SchemaBoard.tsx`
- `frontend/src/components/source-mapper/MappingPreviewPanel.tsx`
- `frontend/src/components/source-mapper/SampleRunReview.tsx`
- `frontend/src/components/source-mapper/VersionHistoryPanel.tsx`
