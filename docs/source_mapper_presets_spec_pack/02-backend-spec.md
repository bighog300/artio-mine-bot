# Source Mapper Presets — Backend Spec

## Design principles

- Reuse the existing source mapper draft/version domain
- Keep v1 simple and source-local
- Save presets as normalized records, not just opaque JSON blobs
- Preserve enough metadata to audit where the preset came from

## Data model

Add a new parent table:

### `source_mapping_presets`

Required fields:

- `id`
- `tenant_id`
- `source_id`
- `name`
- `description` nullable
- `created_from_mapping_version_id` nullable
- `created_by` nullable
- `created_at`
- `updated_at`

Optional v1 metadata fields:

- `row_count`
- `page_type_count`
- `summary_json` nullable
- `tags_json` nullable

Add a new child table:

### `source_mapping_preset_rows`

Required fields:

- `id`
- `preset_id`
- `page_type_key` nullable
- `page_type_label` nullable
- `selector`
- `pattern_type` nullable
- `extraction_mode` nullable
- `attribute_name` nullable
- `destination_entity` nullable
- `destination_field` nullable
- `category_target` nullable
- `transforms_json` nullable
- `confidence_score` nullable
- `is_required`
- `is_enabled`
- `sort_order`
- `rationale_json` nullable
- `created_at`

Notes:
- Structure these columns to match the current mapping row domain closely.
- Do not depend on the source mapping draft row table at runtime after preset creation.
- Preset rows should be a copied snapshot, not live references.

## Migration requirements

Add a new Alembic migration that:

- creates `source_mapping_presets`
- creates `source_mapping_preset_rows`
- adds foreign keys and useful indexes
- cascades delete from preset -> preset rows

Suggested indexes:

- `ix_source_mapping_presets_source_id_created_at`
- `ix_source_mapping_preset_rows_preset_id_sort_order`

## CRUD / service functions

Add backend helpers for:

- `create_source_mapping_preset(...)`
- `list_source_mapping_presets(source_id, tenant_id, ...)`
- `get_source_mapping_preset(preset_id, source_id, tenant_id)`
- `delete_source_mapping_preset(preset_id, source_id, tenant_id)`
- `create_source_mapping_preset_from_version(...)`

### `create_source_mapping_preset_from_version(...)`

This is the key function.

It should:

1. load the target source mapping version or draft
2. load related page types and mapping rows
3. filter rows based on requested statuses, defaulting to approved rows only
4. validate that at least one row remains
5. create the preset parent row
6. copy normalized mapping row data into `source_mapping_preset_rows`
7. store counts/summary metadata
8. return the created preset summary

## API routes

Add a new router, preferably separate from the draft router.

Suggested prefix:

`/sources/{source_id}/mapping-presets`

Implement:

### `GET /sources/{source_id}/mapping-presets`
Returns list of presets for the source.

Response fields per preset:
- `id`
- `name`
- `description`
- `created_from_mapping_version_id`
- `row_count`
- `page_type_count`
- `created_at`
- `updated_at`

### `POST /sources/{source_id}/mapping-presets`
Creates a preset from a draft/version.

Request body:
- `name`
- `description` optional
- `draft_id` or `mapping_version_id`
- `include_statuses` optional, default `["approved"]`

Behavior:
- validate source ownership
- ensure the draft/version belongs to the same source
- create preset and copied preset rows
- return created preset summary

### `DELETE /sources/{source_id}/mapping-presets/{preset_id}`
Deletes a preset and its rows.

Behavior:
- source/tenant validation
- hard delete is acceptable in v1
- return success indicator

## Validation rules

- preset name required
- preset name unique per source in v1, or at least conflict-checked
- cannot create preset with zero matching rows
- cannot create preset from another source's draft/version
- only approved rows by default unless explicitly overridden

## Audit / traceability

Store enough origin metadata to answer:
- which source this preset belongs to
- which mapping version it came from
- when it was created
- how many rows it contains
