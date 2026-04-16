# Operator Visibility Spec

## Goal

Make it obvious in the UI whether a job is:
- running in deterministic mode
- using an applied preset/runtime map
- using AI-assisted mapping
- failing because runtime map is missing

## Required UI/runtime visibility

Expose and/or stream:
- `mode`: `deterministic` or `ai_assisted`
- `runtime_map_source`: `source_structure_map`, `applied_preset`, `ai_generated`, `none`
- current stage
- current URL/item
- records created
- deterministic misses
- heartbeat freshness

## Structured events
Add/stream events like:
- `runtime_mode_selected`
- `preset_applied_runtime_loaded`
- `ai_mapping_skipped`
- `deterministic_page_skipped`
- `record_created`

## UI implications
Jobs/Job Detail/Logs should make it clear:
- why OpenAI was skipped
- what runtime map is being used
- whether deterministic extraction is producing records

## Acceptance criteria
- operator can confirm a job is running successfully without OpenAI
- missing-runtime-map failures are distinguishable from generic crawl failures
