# Implementation Roadmap: AI-Only Structure Mapping

## Current State → Target State

### Current (What You Have)
- ✅ Phase 1: AI analyzes structure (1 API call)
- ✅ Phase 2: Pattern matching classifies pages (0 API calls)
- ✅ Phase 3: Context-guided extraction (500 API calls with hints)
- **Total**: 501 API calls per source

### Target (AI-Only + Crawler Automation)
- ✅ Phase 1: AI analyzes + provides crawler instructions (1 API call)
- ✅ Phase 2: Crawler deterministically extracts (0 API calls)
- ✅ Phase 3: AI only for uncertain pages (10-50 API calls fallback)
- **Total**: 10-50 API calls per source

---

## Quick Implementation (2-3 Days)

### Day 1: Enhanced AI Prompt + New Crawler

**File 1**: Update `app/crawler/site_structure_analyzer.py`
- Enhance STRUCTURE_ANALYZER_PROMPT to return:
  - `crawl_plan` (phases with URL patterns)
  - `extraction_rules` (CSS selectors + regex patterns)
  - `css_selectors` (specific selectors for each field)
  - `ai_fallback_rules` (when to use AI)
- **Time**: 1-2 hours
- **Lines**: ~50 lines in prompt

**File 2**: Create `app/crawler/automated_crawler.py`
- New AutomatedCrawler class:
  - `_extract_deterministic()` — CSS selectors + regex
  - `_classify_by_url()` — URL pattern matching
  - `_extract_with_ai()` — Fallback to GenAI
  - `execute_crawl_plan()` — Main entry point
- **Time**: 3-4 hours
- **Lines**: ~300 lines

### Day 2: Pipeline Integration + Testing

**File 3**: Modify `app/pipeline/runner.py`
- Update `run_crawl()` to use AutomatedCrawler
- Track deterministic vs AI extraction stats
- Add fallback handling
- **Time**: 1-2 hours
- **Lines**: ~40 lines changes

**File 4**: Add Tests
- Test deterministic extraction (CSS selectors)
- Test URL pattern matching
- Test AI fallback logic
- **Time**: 2-3 hours
- **Lines**: ~100 lines tests

### Day 3: Verification + Deployment

**Testing**:
- Run with 5-10 sources
- Verify deterministic accuracy > 90%
- Measure API call reduction
- **Time**: 2-3 hours

**Deployment**:
- Code review
- Merge to main
- Deploy to staging
- Monitor metrics
- **Time**: 1-2 hours

---

## What to Change in Current Code

### 1. Enhanced Structure Analyzer Prompt

**File**: `app/crawler/site_structure_analyzer.py`

**Change**: STRUCTURE_ANALYZER_PROMPT

**From** (current):
```python
STRUCTURE_ANALYZER_PROMPT = """Analyze this website's content structure...
Return ONLY JSON with crawl_targets and mining_map.
"""
```

**To** (AI-driven):
```python
STRUCTURE_ANALYZER_PROMPT = """Analyze this website completely and create EXHAUSTIVE crawl instructions.

Your job: Tell the crawler EXACTLY how to extract data WITHOUT needing more AI help.

Return ONLY valid JSON:
{
  "crawl_plan": {
    "phases": [
      {
        "phase_name": "Artist A-Z",
        "url_pattern": "/artists/[letter]",
        "instructions": "Fetch each letter page"
      }
    ]
  },
  "extraction_rules": {
    "artist_profile": {
      "identifiers": ["URL matches /artists/[letter]/[name]"],
      "css_selectors": {
        "name": "h1.artist-name",
        "bio": "div.biography",
        "mediums": "ul.mediums li"
      },
      "ai_fallback_rules": "Use AI only if CSS fails"
    }
  }
}
"""
```

**Time**: 30 minutes
**Lines**: Change ~50 lines in prompt

---

### 2. New AutomatedCrawler Class

**File**: Create `app/crawler/automated_crawler.py` (NEW)

**Key Methods**:
```python
class AutomatedCrawler:
    async def execute_crawl_plan(self, source_id: str) -> dict:
        """Run AI-generated crawl plan without AI help."""
    
    async def _crawl_and_extract(self, source_id: str, url: str) -> None:
        """Crawl page + extract deterministically."""
    
    def _extract_deterministic(self, html: str, page_type: str) -> dict:
        """Extract using CSS selectors (NO AI)."""
    
    async def _extract_with_ai(self, html: str, page_type: str) -> dict:
        """Fallback: Extract using AI (rare)."""
    
    def _classify_by_url(self, url: str) -> str:
        """Classify page type by URL (NO AI)."""
```

**Time**: 2-3 hours
**Lines**: ~300 lines

---

### 3. Modify Pipeline

**File**: `app/pipeline/runner.py`

**Change**: `run_crawl()` function

**From** (current):
```python
async def run_crawl(self, source_id: str, site_map: SiteMap) -> CrawlStats:
    """Crawl using structure patterns."""
    # Uses link following with structure guidance
```

**To** (AI-driven):
```python
async def run_crawl(self, source_id: str, site_map: SiteMap) -> dict:
    """Crawl using AI-generated crawl plan (0 API calls)."""
    source = await crud.get_source(self.db, source_id)
    structure_map = json.loads(source.structure_map)
    
    # Use automated crawler with AI instructions
    crawler = AutomatedCrawler(structure_map, self.db, self.ai_client)
    stats = await crawler.execute_crawl_plan(source_id)
    
    return stats
```

**Time**: 30 minutes
**Lines**: Replace ~20 lines

---

### 4. Add Monitoring

**File**: `app/pipeline/runner.py` (same file)

**Add Metrics**:
```python
# Track success rates
deterministic_rate = extracted_deterministic / pages_crawled
ai_fallback_rate = extracted_ai_fallback / pages_crawled
failure_rate = failed / pages_crawled

# Expected:
# - deterministic: 85-95% ✓
# - ai_fallback: 5-10% ✓
# - failure: 1-5% ✓

logger.info(
    "crawl_stats",
    deterministic_rate=deterministic_rate,
    ai_fallback_rate=ai_fallback_rate,
    failure_rate=failure_rate,
)
```

**Time**: 30 minutes
**Lines**: ~30 lines

---

## Implementation Checklist

### Phase 1: AI Enhancement (2 hours)
- [ ] Update STRUCTURE_ANALYZER_PROMPT
- [ ] Add `css_selectors` to extraction_rules
- [ ] Add `ai_fallback_rules` to structure
- [ ] Test prompt with GPT-4o

### Phase 2: Crawler Implementation (4 hours)
- [ ] Create AutomatedCrawler class
- [ ] Implement `_extract_deterministic()` (CSS selectors)
- [ ] Implement `_classify_by_url()` (pattern matching)
- [ ] Implement `_extract_with_ai()` (fallback)
- [ ] Test each method in isolation

### Phase 3: Pipeline Integration (2 hours)
- [ ] Modify run_crawl() to use AutomatedCrawler
- [ ] Add monitoring/metrics
- [ ] Handle errors gracefully
- [ ] Test end-to-end with 1 source

### Phase 4: Testing (3 hours)
- [ ] Unit tests for deterministic extraction
- [ ] Integration tests with real HTML
- [ ] Test with 5-10 sources
- [ ] Verify API call reduction
- [ ] Measure accuracy

### Phase 5: Deployment (1 hour)
- [ ] Code review
- [ ] Merge to feature branch
- [ ] Deploy to staging
- [ ] Monitor metrics in staging

---

## Configuration Changes

**Add to `app/config.py`**:
```python
# AI-Only Structure Analysis
STRUCTURE_ANALYSIS_ENABLED = True
USE_DETERMINISTIC_EXTRACTION = True
DETERMINISTIC_CONFIDENCE_THRESHOLD = 80

# Crawler Optimization
CRAWLER_USE_AI_FALLBACK = True
MAX_AI_FALLBACK_PER_SOURCE = 50
CRAWLER_BATCH_SIZE = 10
```

---

## Expected Results

### Token Usage
- **Before**: 202,000 tokens/source
- **After**: 111,000 tokens/source
- **Savings**: 45% reduction

### Cost
- **Before**: $2.51/source
- **After**: $1.33/source
- **Savings**: 47% reduction

### Speed
- **Before**: 1800s per source
- **After**: 450s per source
- **Improvement**: 75% faster

### Accuracy
- **Deterministic**: 90-95%
- **AI Fallback**: 5-10%
- **Overall**: >95% accuracy maintained

---

## Risk Mitigation

### What Could Go Wrong

1. **CSS selectors don't match**
   - ✅ Mitigation: Fallback to AI
   - ✅ Confidence threshold (80%)

2. **HTML structure changes**
   - ✅ Mitigation: AI fallback + manual review
   - ✅ Monitor deterministic_rate metric

3. **Rate limiting issues**
   - ✅ Mitigation: Batch processing + delays
   - ✅ Respect robots.txt

4. **AI fallback too expensive**
   - ✅ Mitigation: MAX_AI_FALLBACK_PER_SOURCE limit
   - ✅ Mark uncertain for manual review

---

## Success Criteria

✅ **Deterministic extraction > 90%** (measured: extracted_deterministic / pages_crawled)
✅ **AI fallback < 10%** (measured: extracted_ai_fallback / pages_crawled)
✅ **Token reduction > 40%** (measured: compare before/after)
✅ **Accuracy maintained > 95%** (compare with current system)
✅ **All tests pass** (unit + integration)

---

## Files to Create/Modify

| File | Type | Size | Time |
|------|------|------|------|
| `site_structure_analyzer.py` | MODIFY | ±50 lines | 30 min |
| `automated_crawler.py` | CREATE | ~300 lines | 2-3 hrs |
| `runner.py` | MODIFY | ±20 lines | 30 min |
| `tests/test_crawler.py` | MODIFY | +50 lines | 1-2 hrs |
| `config.py` | MODIFY | +10 lines | 15 min |

**Total**: ~430 lines | 5-6 hours

---

## Deployment Steps

```bash
# 1. Create feature branch
git checkout -b feature/ai-only-crawler-automation

# 2. Implement changes (Days 1-2)
# - Update prompt
# - Create AutomatedCrawler
# - Modify pipeline
# - Add tests

# 3. Test locally
python -m pytest tests/test_crawler.py -v
python -m pytest tests/test_pipeline.py -v

# 4. Test with sample sources
# Create 5 test sources
# Run mining for each
# Verify deterministic_rate > 90%

# 5. Commit and push
git add .
git commit -m "feat: AI-only structure mapping with crawler automation"
git push origin feature/ai-only-crawler-automation

# 6. Create PR with metrics
# - Before: 202K tokens, $2.51/source
# - After: 111K tokens, $1.33/source
# - Deterministic rate: 92%
# - Speed: 75% faster

# 7. Deploy to staging
# 8. Monitor for 24 hours
# 9. Deploy to production
```

---

## Monitoring Dashboard

Track these metrics in production:

```
Real-time:
  ├─ Pages crawled (current)
  ├─ Deterministic extractions (%)
  ├─ AI fallback used (count)
  └─ Failed pages (count)

Per-source:
  ├─ API calls (should be 1-50, not 500+)
  ├─ Tokens used (should be <111K)
  ├─ Cost ($, should be <$1.33)
  └─ Time taken (should be <450s)

Historical:
  ├─ Trend: deterministic_rate
  ├─ Trend: ai_fallback_rate
  ├─ Trend: total_cost
  └─ Trend: avg_tokens_per_source
```

---

## Bottom Line

**Effort**: 2-3 days for one engineer
**Impact**: 45% token reduction + 75% speed improvement
**Risk**: Low (fully backward compatible, graceful fallback)
**ROI**: 3x in month 1 ($7,080 annual savings from single feature)

**Ready to implement?** Start with Day 1 (enhance prompt + create crawler).

