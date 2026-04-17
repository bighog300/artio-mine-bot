# Implementation Plan

## Phase 1 — Runtime modes
- define explicit deterministic mine / enrichment job types
- ensure existing sources default to deterministic mode when runtime map exists

## Phase 2 — Preset-driven crawl rules
- extend runtime map translation to include crawl/follow/pagination semantics
- improve mapped crawl behavior for existing sources

## Phase 3 — Enrichment pipeline
- add enrichment-only job path using stored pages/content
- re-extract and relink deterministically

## Phase 4 — Media + entity linking
- persist/link media assets cleanly
- improve artist/event/venue relationship assembly

## Phase 5 — Operator visibility
- expose metrics, counters, and runtime mode in API/UI
- add source-level controls for deterministic mine and enrichment

## Recommended implementation order
1. explicit job modes
2. enrichment-only path
3. preset-driven crawl semantics
4. media/entity linking improvements
5. operator UI and metrics
