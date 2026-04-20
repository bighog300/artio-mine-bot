# Art.co.za Pipeline & Mapper Follow-up TODO

## Status
Implementation is deployed and CI is green. Core pipeline, merge logic, and mapper scaffolding are working.

This document tracks **post-deployment improvements and technical debt** identified during review.

---

## 🔴 High Priority

### 1. Fix Image Repetition Detection
**Problem**
- Current logic deduplicates image URLs before counting occurrences.
- This prevents `template_shared` detection from ever triggering.

**Impact**
- Shared/template images are not reliably filtered out.
- Image triage is weaker than expected.

**Tasks**
- [ ] Move repetition counting BEFORE deduplication
- [ ] Track per-page and cross-page image frequency
- [ ] Flag images appearing across multiple artist pages as `template_shared`
- [ ] Ensure `keep=False` for shared/template images by default

---

## 🟠 Medium Priority

### 2. Improve Mapper Preview (Real Artist Family)
**Problem**
- `page_family` is currently synthetic (uses sample URL only)
- Does not reflect actual discovered family structure

**Tasks**
- [ ] Populate real:
  - hub page
  - biography page
  - related pages
- [ ] Show actual URLs discovered during crawl
- [ ] Ensure preview reflects real pipeline output, not placeholders

---

### 3. Ensure Image Preview is Real Data
**Problem**
- `linked_images` / `discarded_images` often empty in preview
- Preview not wired to real structured image payload

**Tasks**
- [ ] Pipe structured image data into preview layer
- [ ] Verify:
  - linked images render correctly
  - discarded images render correctly
- [ ] Add fallback UI states for empty groups

---

## 🟡 Cleanup / Technical Debt

### 4. Test Dependency Consistency
**Problem**
- Repo uses local `respx` shim
- `pytest-asyncio` not clearly declared in all environments

**Tasks**
- [ ] Decide strategy:
  - (A) Use real dependencies (`respx`, `pytest-asyncio`)
  - (B) Keep shim + document clearly
- [ ] Ensure `pyproject.toml` fully reflects test requirements
- [ ] Remove ambiguity between CI vs local environments

---

### 5. Audit All Test Entry Points
**Problem**
- Some environments may still install partial dependencies

**Tasks**
- [ ] Audit:
  - `.github/workflows`
  - `Makefile`
  - scripts/
  - docs
- [ ] Ensure all use:
  ```bash
  pip install -e ".[dev]"
  ```

---

## 🟢 Future Improvements

### 6. Improve Image Classification Confidence
**Ideas**
- [ ] Use DOM region awareness (header/footer/main)
- [ ] Use nearest heading text
- [ ] Add cross-page repetition scoring
- [ ] Introduce confidence thresholds for review queue

---

### 7. Operator UX Enhancements
**Ideas**
- [ ] Add manual override for image roles
- [ ] Add “review low-confidence images” queue
- [ ] Allow toggling keep/discard in UI

---

### 8. Generalize Mapper Heuristics
**Problem**
- Current discovery tweaks slightly biased toward Art.co.za

**Tasks**
- [ ] Validate against another non-artist source
- [ ] Ensure no regression in generic mapping
- [ ] Consider domain-specific presets instead of global bias

---

## ✅ Definition of Done (Next Iteration)

- Image repetition detection is functional and tested
- Mapper preview shows real artist families
- Image preview reflects actual pipeline output
- Test dependencies are clean, consistent, and documented
- No hidden environment assumptions remain

---

## Notes
This is a strong iteration. Core architecture is correct.  
Focus next on **accuracy (image triage)** and **trust (preview realism)**.
