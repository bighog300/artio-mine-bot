# Enrichment Spec

## Goal

Make enrichment a first-class process for existing sources.

## Core concept

Enrichment should improve already-mined data by reprocessing stored pages and existing records using the applied runtime map.

## Required enrichment inputs

- stored raw/source pages
- existing records/entities
- current applied runtime map
- media asset references
- relationship hints from page types

## Enrichment outputs

- updated canonical entities
- missing fields filled
- linked media attached
- artist/event/venue relationships improved
- duplicates or fragments merged more accurately

## Suggested enrichment stages

### 1. Re-extract
Run deterministic extraction again on stored pages using current selectors/rules.

### 2. Relink assets
Capture and attach:
- artist profile images
- event hero/gallery images
- venue images
- documents if supported

### 3. Relationship assembly
Strengthen or create:
- artist ↔ event
- event ↔ venue
- artist ↔ media
- event ↔ media
- venue ↔ media

### 4. Merge
Update canonical records using deterministic merge rules.

## New or extended job types

Suggested job types:
- `mine_source_deterministic`
- `enrich_source_existing_pages`
- `reprocess_source_runtime_map`

## Acceptance criteria

- operator can enrich a known source without recrawling
- existing pages can improve existing records
- media and relationships get stronger over time
