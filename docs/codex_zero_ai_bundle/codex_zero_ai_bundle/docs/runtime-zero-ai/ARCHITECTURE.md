# Architecture: one-time AI discovery, zero-AI runtime mining

## Goal

Move the repository from mixed AI/deterministic mining to a split architecture:

- **Discovery / remapping:** AI allowed
- **Runtime crawl / extraction / enrichment:** AI forbidden

## Core policy

For any source with a published runtime mapping, the system must:
- classify pages deterministically
- extract fields deterministically
- follow links deterministically
- collect assets deterministically
- skip unchanged pages deterministically
- queue failures for review/remapping
- never call AI during runtime jobs

## Lifecycle

### 1. Source created
A source starts without a published runtime mapping.

### 2. Discovery run
The system samples the site and may use AI to produce:
- page types worth mining
- URL patterns
- crawl targets
- pagination/follow rules
- CSS selectors
- regex patterns
- field/entity mapping
- asset rules
- review thresholds

### 3. Mapping draft
Discovery output is stored as a draft mapping version.

### 4. Publish mapping
Publishing compiles/activates the mapping as the source’s runtime contract.

### 5. Runtime crawl
Runtime jobs read only the published mapping and execute deterministically.

### 6. Drift / remapping
If selector hit rate or template patterns degrade, mark mapping stale and queue remapping. Runtime still does not use AI.

## Architecture components

### Discovery layer
Likely centered around:
- `app/crawler/site_structure_analyzer.py`
- `app/source_mapper/*`
- source creation / discovery job entrypoints

Responsibilities:
- sample pages
- cluster page types
- analyze navigation
- optionally call AI
- create mapping drafts
- publish runtime mappings

### Runtime layer
Likely centered around:
- `app/crawler/automated_crawler.py`
- deterministic classification/extraction utilities

Responsibilities:
- load published runtime mapping
- fetch/store page HTML
- compute content hash
- classify by URL patterns / explicit rules
- extract via selectors / regex
- persist records
- follow configured links
- mark review states when rules fail

### Legacy AI extraction layer
Currently centered around:
- `app/pipeline/runner.py`
- `app/ai/classifier.py`
- `app/ai/extractors/*`

Responsibilities after retrofit:
- discovery-only usage
- manual admin/repair tools only if explicitly allowed
- not used by normal runtime crawl jobs for published sources

## Data model additions

## Source
Add or equivalent fields:
- `runtime_mode` (`draft_only`, `deterministic_runtime`)
- `runtime_ai_enabled` (default false for published runtime)
- `published_mapping_version_id`
- `mapping_stale` (bool)
- `last_discovery_run_at`
- `last_mapping_published_at`

## SourceMappingVersion
Create a versioned mapping entity if one does not exist.
Recommended fields:
- `id`
- `source_id`
- `version`
- `status` (`draft`, `published`, `archived`)
- `mapping_json`
- `compiled_runtime_json`
- `created_at`
- `published_at`
- `created_by` / optional

## Page
Add or confirm fields:
- `content_hash`
- `template_hash` (optional but useful)
- `classification_method`
- `extraction_method`
- `review_reason`
- `review_status`
- `mapping_version_id_used`

## Job / stats
Track separately:
- `ai_tokens_discovery`
- `ai_tokens_runtime`
- `selector_hit_rate`
- `unknown_page_count`
- `low_confidence_count`

## Runtime mapping shape

Use a durable JSON structure similar to:

```json
{
  "version": 1,
  "runtime_mode": "deterministic_only",
  "crawl_targets": [
    {
      "url": "https://example.com/artists",
      "page_type": "artist_listing"
    }
  ],
  "page_types": {
    "artist_profile": {
      "detail_page": true,
      "entity_type": "artist",
      "url_patterns": ["/artists/", "/artist/"]
    }
  },
  "extraction_rules": {
    "artist_profile": {
      "css_selectors": {
        "name": ["h1", ".artist-name"],
        "bio": [".bio", ".artist-bio"]
      },
      "regex_patterns": {},
      "required_fields": ["name"],
      "optional_fields": ["bio", "image_urls"],
      "minimum_confidence": 80
    }
  },
  "follow_rules": {
    "artist_listing": {
      "follow_selectors": ["a[href*='/artist/']"],
      "next_page_selectors": ["a[rel='next']", ".pagination-next a"]
    }
  },
  "asset_rules": {
    "artist_profile": {
      "image_selectors": ["img", ".hero img"]
    }
  },
  "review_rules": {
    "queue_low_confidence_pages": true,
    "never_use_ai_fallback": true
  }
}
```

## Runtime algorithm

```text
load published runtime mapping
for each crawl target:
  fetch page
  normalize/store html
  compute content_hash
  if unchanged and mapping version unchanged:
    skip reprocess
    continue

  classify page by url/rules
  if classification fails:
    mark review_reason=unmapped_page_type
    continue

  extract via selectors/regex
  compute confidence from required field hit rate
  if below threshold:
    mark review_reason=low_confidence_extraction
    continue

  save/update record
  collect assets deterministically
  follow child links according to follow rules
```

## Runtime enforcement

Add an explicit runtime AI policy guard.

Suggested policy object or equivalent:
- `job_type`
- `source_runtime_mode`
- `ai_allowed`
- `reason`

All runtime entrypoints should derive this once and pass it through.

If a downstream component tries to call AI when `ai_allowed == false`, either:
- raise a domain-specific exception, or
- short-circuit with a deterministic review state

Do not silently fall back.

## Drift detection

Mark mapping stale if one or more of these happen repeatedly:
- required field hit rate falls below threshold
- unknown page type count rises above threshold
- pagination selectors stop working
- template hash distribution changes materially

Mapping stale should:
- surface in API/UI
- block or warn on future runtime jobs only if severe
- recommend discovery/remapping
- not trigger automatic AI use unless explicitly requested

## Transitional strategy

Keep legacy AI extractors available only for:
- discovery support
- manual admin repair flows
- local/debug workflows

Normal published-source runtime jobs must bypass them.
