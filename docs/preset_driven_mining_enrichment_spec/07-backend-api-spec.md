# Backend API Spec

## Goal

Expose backend operations for preset-driven mining and enrichment.

## Suggested new endpoints

### Source operations
- `POST /api/sources/{source_id}/run-deterministic-mine`
- `POST /api/sources/{source_id}/run-enrichment`
- `POST /api/sources/{source_id}/reprocess-existing-pages`

### Source runtime visibility
- `GET /api/sources/{source_id}/runtime-map`
- `GET /api/sources/{source_id}/enrichment-summary`

### Job metadata
Ensure job/job detail responses include:
- `runtime_mode`
- `runtime_map_source`
- `records_created`
- `records_updated`
- `media_assets_captured`
- `entity_links_created`
- `deterministic_hits`
- `deterministic_misses`

## Implementation notes

- reuse existing job infrastructure
- use separate job types / payloads rather than overloading one path invisibly
- preserve backward compatibility for existing endpoints where reasonable

## Acceptance criteria

- backend exposes first-class deterministic mining and enrichment operations
- job metadata supports operator understanding of outcome quality
