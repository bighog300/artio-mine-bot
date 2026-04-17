# Preset-Driven Crawl Spec

## Goal

Use the applied preset/runtime map to drive crawl behavior for existing sources.

## Required behavior

### Runtime map as crawl policy
The applied preset/runtime map should define or influence:
- entry pages
- page-type patterns
- follow rules
- pagination rules
- extraction selectors
- asset handling rules
- relationship hints

### Page-type-driven expansion
Examples:
- `artist_directory_index`:
  - follow artist profile links
  - follow pagination
  - capture thumbnails as media
- `artist_profile`:
  - extract artist metadata
  - capture profile/gallery images
  - follow linked related exhibitions if allowed
- `event_detail`:
  - extract dates, venue, artists, description
  - capture hero/gallery images
- `venue_detail`:
  - extract venue metadata and images

### Asset handling
Assets such as images/documents should:
- be captured intentionally
- be linked to entities
- not be recursively crawled like ordinary pages

## Required implementation direction

If preset translation currently only provides extraction selectors, extend it so applied runtime maps can also carry:
- `crawl_plan`
- `page_type_rules`
- `follow_rules`
- `asset_rules`

## Acceptance criteria

- existing mapped sources crawl according to preset/runtime rules
- crawl budget is not wasted on generic recursion
- mapped sources produce more relevant detail-page fetches
