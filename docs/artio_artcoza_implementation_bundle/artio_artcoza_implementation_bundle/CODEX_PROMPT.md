You are implementing an Art.co.za artist-family crawl and mapping enhancement inside this repository.

Read first:
- `AGENTS.md`
- `README.md`
- `app/pipeline/runner.py`
- `app/pipeline/image_collector.py`
- `app/extraction/artist_merge.py`
- `app/ai/extractors/artist.py`
- `app/source_mapper/service.py`
- `app/source_mapper/page_clustering.py`
- `app/source_mapper/proposal_engine.py`
- `app/source_mapper/preview.py`
- `app/api/schemas.py`
- `tests/test_pipeline.py`
- `tests/test_artist_enrichment.py`
- `tests/test_source_mapper_phase1.py`

Goal:
Implement a source-specific workflow for `https://www.art.co.za` so the miner can:
1. discover artist pages from `/artists/` and `/artists/[A-Z]`
2. treat `/{slug}/` as the artist profile hub
3. deepen same-family child pages like `about.php` and `art-classes.php`
4. merge all same-family pages into one artist record
5. extract and attach about/bio/news/exhibitions/meta for each artist profile visited
6. link images found on those profile-family pages to the artist record when they are profile, artist-photo, or artwork images
7. dump decorative/template/non-profile images into a discard bucket
8. expose family preview + image triage in Source Mapping UI

Constraints:
- Preserve existing generic behavior for non-Art.co.za sources
- Prefer deterministic domain rules over AI-only discovery for Art.co.za
- Use AI only for normalization / ambiguity resolution, not primary crawl structure discovery
- Keep typing strict and tests updated
- Do not break existing API contracts unless schemas and frontend are updated in the same change

Implement in this order:

## Phase 1 — Crawl/runtime
1. Edit `app/pipeline/runner.py`
   - Add page role inference for:
     - `/artists/` => `artist_directory_root`
     - `/artists/[A-Z]` => `artist_directory_letter`
     - `/{slug}/` => `artist_profile_hub`
     - `/{slug}/about.php` => `artist_biography`
     - `/{slug}/art-classes.php` => `artist_related_page`
   - Extend `_should_ignore_url()` with domain-aware non-artist ignore rules.
   - Extend `_get_same_slug_children()` and `deepen_same_slug_children()` to include fixed suffixes and linked same-family php pages.
   - Ensure `expand_artist_directory_letter()` accepts Art.co.za artist profile URLs and rejects section pages.

2. Update `tests/test_pipeline.py`
   - Add coverage for directory expansion, child page deepening, ignore rules, and family page queueing.

## Phase 2 — Artist merge/output
3. Edit `app/extraction/artist_merge.py`
   - Expand merged payload with:
     - `bio_short`, `bio_full`, `bio_about`, `contact_phone`, `news_items`, `linked_images`, `discarded_images`, `child_pages`, `source_profile_url`, `art_classes`
   - Prefer biography page for canonical long bio.
   - Preserve provenance for all new fields.

4. Edit `app/ai/extractors/artist.py`
   - Normalize structured outputs for `bio`, `about`, `phone`, `news_items`, `exhibitions`, and `page_image_candidates`.

5. Update `tests/test_artist_enrichment.py`
   - Add assertions for biography precedence, provenance, grouped images, discarded images, and normalized child-page merge.

## Phase 3 — Image triage
6. Edit `app/pipeline/image_collector.py`
   - Add roles: `profile`, `artist_photo`, `artwork`, `decorative`, `template_shared`, `unknown`.
   - Return richer image results with `url`, `role`, `confidence`, `keep`, `reason`.
   - Add DOM-zone, heading-context, and repetition heuristics.
   - Default keep only for `profile`, `artist_photo`, and `artwork`.

7. Wire grouped image results back through `app/pipeline/runner.py` into merged artist payloads.

8. Update tests to cover retained vs discarded images.

## Phase 4 — Source Mapper backend
9. Edit `app/source_mapper/service.py`
   - Support `discovery_roots` so scans can begin at `/artists/`.
   - Add second-hop sampling to include letter pages, profile hubs, and biography child pages.

10. Edit `app/source_mapper/page_clustering.py`
    - Add cluster rules for `artist_directory_root`, `artist_directory_letter`, `artist_profile_hub`, `artist_biography`, `artist_related_page`.

11. Edit `app/source_mapper/proposal_engine.py`
    - Add artist-focused field proposals for name, bio/about, contact, avatar/profile image, artwork image groups, exhibition links.

12. Edit `app/source_mapper/preview.py`
    - Extend preview output with page family, field sources, linked images, discarded images, and warnings.

13. Edit `app/api/schemas.py`
    - Add schemas for richer preview payloads.

14. Update `tests/test_source_mapper_phase1.py`
    - Add coverage for discovery roots, artist-family clusters, and family/image preview payloads.

## Phase 5 — Frontend Source Mapping UX
15. Edit `frontend/src/lib/api.ts`
    - Add types for field provenance, image preview groups, and family preview payloads.

16. Edit `frontend/src/pages/SourceMapping.tsx`
    - Reframe flow into discovery setup, page type samples, record preview, image triage, save preset.

17. Edit components:
    - `frontend/src/components/source-mapper/MappingPreviewPanel.tsx`
    - `frontend/src/components/source-mapper/PageTypeSidebar.tsx`
    - `frontend/src/components/source-mapper/ScanSetupForm.tsx`
   Add family page list, field provenance, linked/discarded image panes, and discovery-root / ignore-pattern controls.

18. Update frontend tests where needed.

Implementation details to use:

### Art.co.za mapping preset
```json
{
  "source": "https://www.art.co.za",
  "discovery_roots": ["https://www.art.co.za/artists/"],
  "page_role_overrides": {
    "https://www.art.co.za/artists/": "artist_directory_root"
  },
  "patterns": {
    "directory_letter": "^/artists/[A-Z]$",
    "artist_profile": "^/[^/]+/?$",
    "artist_biography": "^/[^/]+/about\\.php$",
    "artist_related": "^/[^/]+/art-classes\\.php$"
  },
  "same_slug_children": ["about.php", "art-classes.php"],
  "ignore_url_patterns": [
    "/watchlist",
    "/my",
    "/auctions",
    "/training",
    "/galleries",
    "facebook",
    "instagram",
    "mailchimp"
  ]
}
```

### Expected behavior on a sample artist
Use `https://art.co.za/cornevaneck/` as the representative sample:
- hub page should classify as `artist_profile_hub`
- `/cornevaneck/about.php` should supply canonical long bio and exhibitions
- `/cornevaneck/art-classes.php` should merge as related child content
- images from these pages should be grouped into linked vs discarded buckets

Deliverables:
- code changes
- updated tests
- no broken existing tests
- concise changelog in the final response

Validation commands:
```bash
python -m pytest tests/test_pipeline.py -q
python -m pytest tests/test_artist_enrichment.py -q
python -m pytest tests/test_source_mapper_phase1.py -q
```

If time permits, run broader relevant tests too.
