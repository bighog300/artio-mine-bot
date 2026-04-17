# Operator UI Spec

## Goal

Expose clear controls for preset-driven mining and enrichment on existing sources.

## Required source-level controls

For a source with an applied preset/runtime map, operators should be able to trigger:

- `Run deterministic mine`
- `Run enrichment`
- `Reprocess existing pages`
- `View active runtime map`
- `Show deterministic misses`
- `Show linked media count`

## Required visibility

Display:
- runtime mode
- active preset/runtime map source
- records created/updated
- deterministic extraction hits
- deterministic misses
- media assets captured
- entity links created
- merge/update counts

## Suggested UI surfaces

- Source detail / operations page
- Jobs page / job detail
- Source operations console
- Source run history

## Acceptance criteria

- operator can run mining or enrichment intentionally
- UI distinguishes network progress from business progress
- known sources show whether preset-driven mode is being used
