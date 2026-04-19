# Task breakdown for Codex

## Epic 1 — Data model and migration

### Task 1.1
Add source runtime lifecycle fields.

Suggested fields:
- `runtime_mode`
- `runtime_ai_enabled`
- `published_mapping_version_id`
- `mapping_stale`
- `last_discovery_run_at`
- `last_mapping_published_at`

### Task 1.2
Create `SourceMappingVersion` model/table if missing.

### Task 1.3
Add page metadata fields:
- `content_hash`
- `template_hash` (optional)
- `classification_method`
- `extraction_method`
- `review_reason`
- `review_status`
- `mapping_version_id_used`

### Task 1.4
Create migration(s) and update CRUD/schemas.

---

## Epic 2 — Runtime policy enforcement

### Task 2.1
Create a runtime policy helper/module.

Suggested behavior:
- derive policy from job type + source state
- `ai_allowed` true only for discovery/remapping/manual explicit admin workflows
- `ai_allowed` false for published-source runtime crawl/enrichment

### Task 2.2
Enforce policy in runtime entrypoints.

### Task 2.3
Enforce policy inside AI client/classifier/extractor call sites or wrappers to fail closed.

---

## Epic 3 — Discovery and publishable mapping

### Task 3.1
Refactor discovery output into a versioned mapping draft.

### Task 3.2
Add runtime mapping compiler.

Inputs:
- discovery output
- page clusters
- selector proposals
- URL patterns

Outputs:
- compiled runtime JSON used by deterministic runtime

### Task 3.3
Add mapping publish action and activate published mapping on source.

---

## Epic 4 — Deterministic runtime routing

### Task 4.1
Change runtime job routing so published sources use deterministic executor.

### Task 4.2
Ensure deterministic classification uses runtime mapping URL/page rules only.

### Task 4.3
Ensure deterministic extraction uses selector/regex rules only.

### Task 4.4
Ensure follow/pagination and asset collection use runtime mapping only.

---

## Epic 5 — Hash-based skip and record updates

### Task 5.1
Compute normalized page content hash during fetch/store.

### Task 5.2
Skip runtime reprocessing if content hash and mapping version are unchanged.

### Task 5.3
Store mapping version used for each extraction.

---

## Epic 6 — Review queue instead of AI fallback

### Task 6.1
Define review reasons enum/constants.

Suggested values:
- `unmapped_page_type`
- `low_confidence_extraction`
- `selector_miss`
- `mapping_stale`
- `unexpected_template`

### Task 6.2
Update runtime flow to persist review states instead of invoking AI.

### Task 6.3
Add API exposure for review queue / review reasons.

---

## Epic 7 — Drift detection

### Task 7.1
Track extraction success metrics per page type and source.

### Task 7.2
Mark mapping stale when thresholds degrade.

### Task 7.3
Expose stale mapping state in source stats/API.

---

## Epic 8 — Tests

### Unit tests
- runtime policy derivation
- AI guard raises or blocks correctly
- mapping compiler output shape
- content hash skip behavior
- review reason assignment

### Integration tests
- discovery run creates a mapping draft
- publish activates runtime mapping
- runtime crawl for published source triggers zero AI calls
- unmapped page becomes review item
- stale mapping flag flips under degraded extraction conditions

---

## Deliverable commits

Suggested commit sequence:
1. `feat: add source runtime mapping lifecycle schema`
2. `feat: add runtime AI policy enforcement`
3. `feat: persist discovery drafts and publish runtime mappings`
4. `feat: route published-source crawls through deterministic runtime`
5. `feat: skip unchanged pages by content hash`
6. `feat: replace runtime AI fallback with review queue`
7. `feat: detect mapping drift and stale runtime mappings`
8. `test: cover zero-ai runtime mining flow`
9. `docs: add runtime mapping and discovery workflow docs`
