# AI Source Mapper — Test Plan

## 1. Test goals

Verify that the feature is safe, accurate enough for admin moderation, and does not create unintended production data.

## 2. Backend tests

### CRUD / model tests
- create mapping draft
- create page type cluster
- create mapping rows
- update row statuses
- publish version
- enforce one active published version per source
- rollback behavior

### API tests
- create mapping draft returns 201
- scan start returns queued state
- page types list returns detected clusters
- row update validates destination field allowlist
- preview endpoint returns record preview without creating records
- sample run endpoints return sample results
- publish endpoint updates source active mapping version

### Failure-path tests
- invalid source returns 404
- publish without approved mappings returns 409
- preview with broken sample returns partial warning instead of 500 where possible
- duplicate concurrent scan request returns safe conflict/accepted response

## 3. Frontend tests

### Component tests
- mapping matrix renders rows
- row inline edit updates local draft state
- filters narrow rows correctly
- preview panel renders extraction + destination preview
- publish modal shows version summary

### Interaction tests
- bulk approve updates selected rows
- drag-and-drop changes destination entity/field
- switching page type updates samples
- unsaved change warning appears when leaving workspace

## 4. Integration tests

- create source -> open mapping -> run scan -> moderate rows -> preview -> publish
- published mapping used by mining flow on next run
- rescan does not overwrite published mapping automatically

## 5. Manual QA checklist

### Scan setup
- paste URL
- edit scan options
- see normalized URL and warnings
- save and run scan

### Matrix moderation
- sort by confidence
- filter by page type
- approve row
- reject row
- edit destination field
- bulk approve selected rows

### Preview
- open preview for sample page
- confirm highlighted source field
- confirm destination entity/field
- confirm category target
- verify no production records created

### Publish
- publish reviewed draft
- see version history entry
- rollback to previous version
- confirm source points to active version

## 6. Regression coverage

Because this repo already supports source creation, mining, and review, regression-check:
- source creation still works without mapper usage
- start discovery and full mining actions still work
- existing extraction rules flow still works when no mapping version is published
- source detail page remains functional with/without mapping data

## 7. Performance guardrails

- scan should cap sample volume in MVP
- list rows endpoint should paginate
- preview should only process selected sample pages
- matrix should remain usable with 100+ mapping rows

## 8. UAT sign-off scenarios

### Scenario A — Event site
Admin can scan an event site, identify event detail pages, map title/date/venue fields, preview event records, and publish.

### Scenario B — Artist site
Admin can scan an artist/gallery site, map artist bio/media/contact fields, preview artist records, and publish.

### Scenario C — Rescan after site redesign
Admin can rescan a site, compare changed proposals to current published version, and keep existing published mapping until the new draft is approved.
