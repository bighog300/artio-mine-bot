# Task checklist

## Backend crawl and merge
- [ ] Add Art.co.za-specific role inference in `app/pipeline/runner.py`
- [ ] Add ignore URL patterns for non-artist sections
- [ ] Add same-slug child page support for `about.php` and `art-classes.php`
- [ ] Extend artist merge payload in `app/extraction/artist_merge.py`
- [ ] Prefer biography page as canonical long bio source
- [ ] Preserve `child_pages` and field provenance

## Image triage
- [ ] Expand image roles in `app/pipeline/image_collector.py`
- [ ] Return linked vs discarded image groups
- [ ] Add repetition/template-image heuristic
- [ ] Pass grouped image results through `runner.py`

## Source Mapper backend
- [ ] Add `discovery_roots` support in `app/source_mapper/service.py`
- [ ] Add artist-family page clustering
- [ ] Add artist-focused proposal generation
- [ ] Extend preview payload with family + image groups
- [ ] Update `app/api/schemas.py`

## Frontend
- [ ] Update mapping API types
- [ ] Add family preview panel
- [ ] Add image triage preview
- [ ] Add discovery-root / ignore-pattern controls
- [ ] Extend Source Mapping tests

## Tests
- [ ] `tests/test_pipeline.py`
- [ ] `tests/test_artist_enrichment.py`
- [ ] `tests/test_source_mapper_phase1.py`
