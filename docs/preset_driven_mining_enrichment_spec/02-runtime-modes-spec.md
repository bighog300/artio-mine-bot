# Runtime Modes Spec

## Goal

Separate mining and enrichment into explicit operational modes for existing sources.

## Required runtime modes

### 1. Preset-driven mine
Used when:
- source has `active_mapping_preset_id`
- or source has a usable runtime map

Behavior:
- load runtime map
- skip AI mapping
- crawl deterministically
- extract deterministically
- capture linked media assets
- assemble/update records

### 2. Enrichment-only
Used when:
- source already has stored pages/content
- operator wants to improve records without a full recrawl

Behavior:
- do not recrawl the source
- load stored pages/content from DB
- re-run deterministic extraction using current applied runtime map
- relink media and relationships
- merge fragments into canonical records

### 3. Refresh with AI assist
Used when:
- operator explicitly wants to improve mappings
- runtime map is missing or incomplete
- AI-assisted mapping is allowed

Behavior:
- run AI only when explicitly requested/allowed
- not the default path for known sources

## Source selection logic

For existing sources:
- if runtime map exists, default to preset-driven mine
- if operator chooses enrichment, skip crawl and operate on stored content
- if runtime map missing, either fail clearly or allow AI-assisted refresh

## Acceptance criteria

- runtime mode is explicit and visible
- known mapped sources do not default back to AI mapping
- enrichment can run without a recrawl
