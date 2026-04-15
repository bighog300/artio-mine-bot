# Sprint C: Guided Source Setup and Crawl Settings UX

## Objective
Reduce operator error by turning source creation and source configuration into a guided crawl setup experience.

## Scope

### Frontend
Update:
- `frontend/src/pages/Sources.tsx`
- `frontend/src/pages/SourceDetail.tsx`
- `frontend/src/lib/api.ts`

Add or improve in source creation modal:
- URL
- Name
- Crawl intent
- Max pages
- Max depth
- Enabled
- Crawl hints
- Extraction rules

Buttons:
- Save Source
- Save & Start Discovery
- Save & Start Full Mining

Crawl intent options:
- Site root
- Directory/listing page
- Detail/entity page
- Test crawl

Add Source Detail Settings tab:
- enabled
- max_depth
- extraction_rules
- crawl_hints
- ignore patterns
- same-slug child patterns
- source name

Optional preflight panel:
- normalized URL
- duplicate source detection
- probable page type
- recommended crawl strategy
- domain summary

### Backend
Update:
- `app/api/routes/sources.py`
- `app/api/schemas.py`
- `app/db/crud.py`

Add optional endpoint:
- `POST /api/sources/preflight`

Preflight response may include:
- normalized_url
- existing_source_id
- existing_source_url
- probable_page_type
- recommended_mode
- domain
- warnings

## UX Requirements
- Split “save” from “start mining” so operators can configure before launching.
- Keep advanced settings hidden by default but easy to expand.
- Validate JSON-like fields such as crawl hints before save.
- Warn clearly when the source URL already exists.

## Acceptance Criteria
- Operators can create a source without automatically launching it.
- Operators can choose discovery-only or full mining at creation time.
- Source settings are editable after creation.
- Duplicate or risky URLs are flagged before launch.
- Guided setup reduces incorrect crawl starts.

## Notes
This sprint should prioritize operator confidence over minimizing clicks.
