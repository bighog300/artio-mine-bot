# Concrete implementation plan for the uploaded repo

## Phase 1 — Make Art.co.za crawl correctly

### 1. Edit `app/pipeline/runner.py`

Implement a source-specific crawl preset using existing crawl hint style hooks.

#### Add / extend
- page-role inference for:
  - `/artists/` → `artist_directory_root`
  - `/artists/[A-Z]` → `artist_directory_letter`
  - `/{slug}/` → `artist_profile_hub`
  - `/{slug}/about.php` → `artist_biography`
  - `/{slug}/art-classes.php` → `artist_related_page`
- domain-aware ignore rules for non-artist sections
- same-slug child discovery using fixed suffixes and linked same-family php pages

#### Functions to edit first
1. `_get_same_slug_children()`
2. `_should_ignore_url()`
3. `expand_artist_directory_letter()`
4. `deepen_same_slug_children()`
5. page-role inference path used before `handle_discovery_page()`
6. `process_artist_related_page()`

#### Acceptance criteria
- `/artists/A` expands to artist slug pages like `/cornevaneck/`
- `/cornevaneck/` deepens to `/cornevaneck/about.php` and `/cornevaneck/art-classes.php`
- ignored sections are skipped
- same-family related pages are discoverable without breaking current generic sources

### 2. Edit `tests/test_pipeline.py`

Add tests for:
- directory root and letter page expansion
- same-slug child discovery
- ignore rules for non-artist sections
- preservation of artist family page queueing

---

## Phase 2 — Make merged artist records match the desired output

### 3. Edit `app/extraction/artist_merge.py`

Expand the merged artist payload.

#### Add fields
- `bio_short`
- `bio_full`
- `bio_about`
- `contact_phone`
- `news_items`
- `linked_images`
- `discarded_images`
- `child_pages`
- `source_profile_url`
- `art_classes`

#### Merge rules
- prefer biography page for canonical long bio
- merge exhibitions from biography and related pages
- preserve child page provenance
- merge grouped image roles instead of a flat image list only

#### Functions / sections to edit
1. `PROVENANCE_FIELD_MAP`
2. `merge_artist_payload()`
3. image grouping merge logic
4. completeness inputs for new fields

### 4. Edit `app/ai/extractors/artist.py`

Keep extraction generic, but normalize structured fields better.

#### Add support for optional normalized outputs
- `bio`
- `about`
- `phone`
- `news_items`
- `exhibitions`
- `page_image_candidates`

### 5. Edit `tests/test_artist_enrichment.py`

Add tests for:
- biography page winning for long bio
- child page provenance preservation
- grouped image role merge
- discarded image storage
- normalized exhibitions/news merge

---

## Phase 3 — Separate linked images from dumped images

### 6. Edit `app/pipeline/image_collector.py`

#### Expand image roles
- `profile`
- `artist_photo`
- `artwork`
- `decorative`
- `template_shared`
- `unknown`

#### Add keep/drop behavior
Return a richer image result with:
- `url`
- `role`
- `confidence`
- `keep`
- `reason`

#### Heuristics to add
- DOM zone awareness: header/footer/nav/sidebar should push toward discard
- heading/context awareness: `about`, `recent work`, `artworks`, `artist photo`
- repetition heuristic: images repeated across many artist pages become `template_shared`
- keep only `profile`, `artist_photo`, `artwork` by default

### 7. Edit `app/pipeline/runner.py` again

Wire grouped image output into raw artist data before merge.

### 8. Add / update tests
- profile images are retained
- artwork images are retained
- decorative/template images are discarded
- merged artist record stores both linked and discarded groups

---

## Phase 4 — Make Source Mapper understand artist families

### 9. Edit `app/source_mapper/service.py`

Add discovery-root support so scans can start at `/artists/` instead of homepage only.

#### Add
- `discovery_roots` support in scan options / source hints
- second-hop sampling from:
  - directory root
  - letter pages
  - profile hubs
  - biography child pages

### 10. Edit `app/source_mapper/page_clustering.py`

Add clustering rules for:
- `artist_directory_root`
- `artist_directory_letter`
- `artist_profile_hub`
- `artist_biography`
- `artist_related_page`

### 11. Edit `app/source_mapper/proposal_engine.py`

Add artist-page field proposals:
- artist name
- bio/about
- contact email/phone
- avatar/profile image
- artwork image groups
- exhibition links

### 12. Edit `app/source_mapper/preview.py`

Expand preview output to include:
- page family
- field sources
- linked images
- discarded images
- warnings

### 13. Edit `app/api/schemas.py`

Add schema support for richer preview payloads.

---

## Phase 5 — Upgrade the Source Mapping UI

### 14. Edit frontend API typing
- `frontend/src/lib/api.ts`

Add interfaces for:
- field source provenance
- image preview groups
- family preview payloads

### 15. Edit `frontend/src/pages/SourceMapping.tsx`

Reframe the flow into:
1. discovery setup
2. page type samples
3. record preview
4. image triage
5. save preset

### 16. Edit Source Mapper components
- `frontend/src/components/source-mapper/MappingPreviewPanel.tsx`
- `frontend/src/components/source-mapper/PageTypeSidebar.tsx`
- `frontend/src/components/source-mapper/ScanSetupForm.tsx`

Add:
- artist family page list
- field provenance display
- linked vs discarded image panes
- discovery-root and ignore-pattern inputs

### 17. Extend frontend tests
- `frontend/src/components/source-mapper/SourceMapperCriticalFlows.test.tsx`

---

## Data contract recommendation

Use a source/domain preset like this for Art.co.za:

```json
{
  "page_role_overrides": {
    "https://www.art.co.za/artists/": "artist_directory_root"
  },
  "directory_roots": ["/artists/"],
  "directory_letter_pattern": "^/artists/[A-Z]$",
  "artist_profile_pattern": "^/[^/]+/?$",
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

## Suggested ticket breakdown

### Ticket 1
Add Art.co.za artist-family crawl preset.

### Ticket 2
Add artist image triage and discard bucket.

### Ticket 3
Add Source Mapper preview for artist family + image triage.
