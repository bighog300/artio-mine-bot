# Data Model

## Core entities

### SourceProfile
Represents a profiling run against a source seed URL.

Fields:
- id
- source_id
- seed_url
- started_at
- completed_at
- status
- site_fingerprint
- sitemap_urls
- nav_discovery_summary
- profile_metrics_json

### UrlFamily
Represents a clustered family of structurally similar URLs.

Fields:
- id
- source_profile_id
- family_key
- family_label
- path_pattern
- page_type_candidate
- confidence
- sample_urls_json
- follow_policy_candidate
- pagination_policy_candidate
- include_by_default
- diagnostics_json

### SourceMappingVersion
Represents a versioned mapping approved or drafted for a source.

Fields:
- id
- source_id
- version_number
- status (draft, approved, superseded, archived)
- created_at
- approved_at
- created_by
- based_on_profile_id
- notes
- mapping_json

### SourceMappingFamilyRule
Represents one approved family rule within a mapping version.

Fields:
- id
- mapping_version_id
- family_key
- page_type
- include
- crawl_priority
- follow_links
- pagination_mode
- extraction_strategy
- freshness_policy
- selectors_json
- overrides_json

### CrawlRunCheckpoint
Represents persisted crawl-run progress.

Fields:
- id
- crawl_run_id
- mapping_version_id
- status
- last_checkpoint_at
- frontier_counts_json
- progress_json
- last_processed_url
- worker_state_json

### FrontierUrl
Represents one durable URL in the crawl frontier.

Fields:
- id
- source_id
- mapping_version_id
- normalized_url
- canonical_url
- family_key
- discovered_from_url
- depth
- status
- priority
- skip_reason
- retry_count
- last_error
- content_hash
- etag
- last_modified
- first_discovered_at
- last_fetched_at
- next_eligible_fetch_at
- last_extracted_at
- diagnostics_json

### MappingDriftSignal
Represents one drift detection event or anomaly.

Fields:
- id
- source_id
- mapping_version_id
- family_key
- signal_type
- severity
- detected_at
- metrics_json
- sample_urls_json
- resolution_status
- proposed_action

## Minimal implementation strategy

Start with:
- SourceProfile
- UrlFamily
- SourceMappingVersion
- FrontierUrl
- CrawlRunCheckpoint

Then add:
- MappingDriftSignal
- family-level rule tables if needed beyond JSON storage
