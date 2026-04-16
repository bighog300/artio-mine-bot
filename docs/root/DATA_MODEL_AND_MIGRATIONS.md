# AI Source Mapper — Data Model and Migration Plan

## 1. Overview

The feature needs versioned mapping storage separate from existing `sources`, `pages`, and `records` tables.

Recommended approach:
- keep `Source` as the owner
- add mapping draft/version tables
- add mapping row tables
- add sampled page snapshots / scan results
- add sample extraction review runs
- store active published version on `sources`

## 2. Existing tables to reuse

- `sources`
- `pages`
- `records`
- `jobs`
- `activity_logs` or equivalent logging/audit tables if present

## 3. Proposed additions to `Source`

Add columns:
- `active_mapping_version_id` nullable FK
- `mapping_status` nullable string (`none`, `draft`, `published`, `error`)
- `last_mapping_scan_at` nullable datetime
- `last_mapping_error` nullable text

## 4. New tables

### 4.1 `source_mapping_versions`
Stores a versioned draft or published mapping set.

Suggested columns:
- `id`
- `tenant_id`
- `source_id`
- `version_number`
- `status` (`draft`, `published`, `archived`)
- `scan_status` (`pending`, `queued`, `running`, `completed`, `error`)
- `scan_options_json`
- `summary_json`
- `created_by`
- `published_by`
- `published_at`
- `created_at`
- `updated_at`

Indexes:
- `(source_id, status)`
- `(source_id, version_number)` unique

### 4.2 `source_mapping_page_types`
Stores discovered page-type clusters for a draft.

Suggested columns:
- `id`
- `mapping_version_id`
- `key`
- `label`
- `sample_count`
- `confidence_score`
- `classifier_signals_json`
- `created_at`

Indexes:
- `(mapping_version_id, key)` unique

### 4.3 `source_mapping_samples`
Stores sampled pages or references to page snapshots used in scan/preview.

Suggested columns:
- `id`
- `mapping_version_id`
- `page_id` nullable FK to `pages`
- `page_type_id` nullable FK
- `url`
- `title`
- `html_snapshot`
- `dom_summary_json`
- `structured_data_json`
- `created_at`

Indexes:
- `(mapping_version_id, page_type_id)`

### 4.4 `source_mapping_rows`
Stores individual field mappings.

Suggested columns:
- `id`
- `mapping_version_id`
- `page_type_id`
- `selector`
- `pattern_type`
- `extraction_mode`
- `attribute_name` nullable
- `sample_value`
- `destination_entity`
- `destination_field`
- `category_target` nullable
- `transforms_json`
- `confidence_score`
- `confidence_reasons_json`
- `status`
- `is_required`
- `is_enabled`
- `sort_order`
- `created_at`
- `updated_at`

Indexes:
- `(mapping_version_id, status)`
- `(mapping_version_id, destination_entity)`
- `(page_type_id, destination_entity, destination_field)`

### 4.5 `source_mapping_sample_runs`
Stores sample extraction review runs.

Suggested columns:
- `id`
- `mapping_version_id`
- `status`
- `sample_count`
- `created_by`
- `created_at`
- `completed_at`
- `summary_json`

### 4.6 `source_mapping_sample_results`
Stores preview results for sample extraction runs.

Suggested columns:
- `id`
- `sample_run_id`
- `sample_id`
- `record_preview_json`
- `review_status`
- `review_notes`
- `created_at`
- `updated_at`

## 5. SQLAlchemy model sketch

Recommended file changes:
- `app/db/models.py`
- `app/db/crud.py`
- `app/api/schemas.py`

Potential model names:
- `SourceMappingVersion`
- `SourceMappingPageType`
- `SourceMappingSample`
- `SourceMappingRow`
- `SourceMappingSampleRun`
- `SourceMappingSampleResult`

## 6. Migration plan

### Migration 1
Add source-level mapping fields and create `source_mapping_versions`.

### Migration 2
Create page types, samples, and rows tables.

### Migration 3
Create sample run + sample result tables.

### Migration 4
Backfill `mapping_status = none` for existing sources and null active mapping version.

## 7. Data lifecycle rules

- deleting a source should cascade delete its mapping drafts and samples
- deleting a published version should not be allowed if active
- rolling back should create a new draft or switch active reference with audit logging
- preview/sample-run data should remain separate from production `records`

## 8. Storage and size concerns

HTML snapshots may be large.
Recommended MVP approach:
- store truncated HTML snapshots or compact DOM summaries
- keep a configurable cap on sample size
- reuse existing `pages.html` where possible

## 9. Validation rules

- destination entity must match supported record types
- destination field must be in an allowlist per entity
- one active published version per source
- publish blocked if no approved rows exist
- publish blocked if draft scan failed and no manual override is present
