# Preset Application Spec

## Goal

Make saved mapping presets operationally useful at runtime.

Right now presets exist as stored snapshots. They must be usable by the crawler and extractor.

## Required behavior

### Option preferred for this repo
Add an **Apply Preset to Source** workflow.

A preset should be translatable into source runtime configuration such as:
- `structure_map`
- `crawl_hints`
- deterministic extraction rules
- page-type rules
- relationship/asset hints if supported

## Proposed source-level fields
The source should track runtime mapping state, for example:
- `active_mapping_preset_id` nullable
- `structure_map`
- `crawl_hints`
- `runtime_mapping_updated_at`

## Required backend operations
Add helpers like:
- `apply_source_mapping_preset_to_source(source_id, preset_id, ...)`
- `build_runtime_map_from_preset(preset_id) -> dict`
- `get_active_runtime_map(source_id) -> dict | None`

## Translation requirements

The preset-to-runtime translation should produce enough information for:
- page-type classification
- field extraction
- crawl-follow logic
- optional asset-role hints

### Minimal acceptable v1
A preset must be able to define:
- field extraction rules
- URL/page-type match hints
- page-type labels
- deterministic extraction selectors

### Better v1
Also include:
- follow rules
- pagination behavior
- asset handling rules

## New API routes
Suggested:
- `POST /api/sources/{source_id}/mapping-presets/{preset_id}/apply`
- `GET /api/sources/{source_id}/runtime-map`

## Acceptance criteria
- operator can apply a saved preset to a source
- source runtime config is updated from the preset
- future crawls use the applied runtime config without requiring OpenAI
