# Crawl and Extraction Spec

## Goal

Ensure crawl and extraction can run deterministically from applied runtime rules.

## Crawl requirements

### Deterministic-first crawl
If a runtime map exists:
- classify pages using runtime rules first
- expand links using mapped follow rules
- avoid generic fallback recursion whenever structured rules are available

### OpenAI-free operation
When `ai_client is None`:
- do not attempt AI mapping
- do not attempt AI classification/extraction
- continue using deterministic rules only
- log deterministic misses explicitly

## Extraction requirements

### Deterministic-first extraction
For each page:
1. classify with runtime structure/preset rules
2. if page type matched and extraction rules exist, extract deterministically
3. only attempt AI fallback if AI is enabled and available
4. otherwise skip with a clear reason

### Skip behavior
When a page cannot be classified or extracted deterministically and no AI is available:
- do not crash the whole job
- emit a structured skip event
- continue processing other pages

## Required events
Emit events such as:
- `runtime_map_loaded`
- `runtime_map_missing`
- `ai_mapping_skipped_existing_runtime_map`
- `deterministic_classification_hit`
- `deterministic_extraction_hit`
- `deterministic_extraction_miss`
- `page_skipped_no_runtime_rule`

## Acceptance criteria
- crawl/extract completes without OpenAI when runtime map exists
- deterministic misses are visible but not fatal by default
- record extraction proceeds from mapped selectors/rules
