# Preset-Driven Mining + Enrichment for Existing Sources — Overview

## Goal

Improve the ingestion system so existing sources with a saved preset mapping or usable runtime map can:
- mine deterministically
- enrich existing content deterministically
- avoid unnecessary OpenAI usage
- improve record completeness over time

This feature targets sources that are already known and mapped, such as artist directories, event/exhibition sources, and venue-oriented sites.

## Product intent

For an existing source with an applied preset/runtime map, the system should behave like a stable structured ingestor:

1. load the runtime map
2. skip AI mapping
3. crawl deterministically
4. extract deterministic fields and linked assets
5. assemble/merge entities
6. enrich existing records and pages incrementally

## Why this matters

Many existing sources already have useful mappings. They should not need fresh AI mapping for every run.

The current direction should evolve toward:
- preset-driven mining as the default for known sources
- enrichment as a first-class workflow
- media linking and entity completeness improvements
- deterministic operation with clear operator visibility

## Scope

This spec covers:
- preset-driven mining runs
- enrichment-only runs using existing stored pages/content
- deterministic media capture and linking
- entity assembly/merge improvements
- operator controls and visibility for known mapped sources

Out of scope for this pack:
- new-source AI mapping UX
- global preset libraries
- fully generalized ML ranking/dedup beyond deterministic entity merge improvements
