# Artio Miner — Art.co.za implementation bundle

This bundle packages a concrete implementation plan and an execution-ready Codex prompt for the uploaded repo.

## Files
- `CODEX_PROMPT.md` — paste into Codex to execute the implementation
- `IMPLEMENTATION_PLAN.md` — phased file-by-file plan
- `TASK_CHECKLIST.md` — concise engineering checklist
- `ARTCOZA_MAPPING_SPEC.json` — proposed source/domain mapping for `art.co.za`

## Goal
Implement a source-specific crawl and extraction workflow for Art.co.za:
1. Discover artist profile URLs from `/artists/` and `/artists/[A-Z]`
2. Treat `/{slug}/` as the artist profile hub
3. Deepen same-family pages like `/about.php` and `/art-classes.php`
4. Merge those pages into a single artist record
5. Attach artist/profile/artwork images to the record
6. Dump decorative/template/non-profile images into a discard bucket
7. Expose family preview + image triage in Source Mapping UI

## Suggested execution order
1. `app/pipeline/runner.py`
2. `tests/test_pipeline.py`
3. `app/extraction/artist_merge.py`
4. `app/ai/extractors/artist.py`
5. `tests/test_artist_enrichment.py`
6. `app/pipeline/image_collector.py`
7. `app/source_mapper/service.py`
8. `app/source_mapper/page_clustering.py`
9. `app/source_mapper/proposal_engine.py`
10. `app/source_mapper/preview.py`
11. `app/api/schemas.py`
12. frontend files under `frontend/src/pages/SourceMapping.tsx` and `frontend/src/components/source-mapper/*`

## Validation
Run at minimum:
- `python -m pytest tests/test_pipeline.py -q`
- `python -m pytest tests/test_artist_enrichment.py -q`
- `python -m pytest tests/test_source_mapper_phase1.py -q`
