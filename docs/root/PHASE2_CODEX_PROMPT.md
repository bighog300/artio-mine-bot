# Phase 2 Codex Execution Prompt

## Copy & Paste This Into Codex

---

```
You are implementing Phase 2 of the Artio Miner token optimization: AI-Only Structure Mapping + Crawler Automation.

Reference Documents:
- NEXT_PHASE_SUMMARY.md (overview, timeline, metrics)
- AI_ONLY_STRUCTURE_MAPPING.md (complete design with code examples)
- AI_ONLY_QUICK_START.md (implementation checklist, day-by-day plan)

Current State: Phase 1 is complete (52% token reduction). Phase 2 will add 45% more reduction for 73.6% total.

## Phase 2: AI-Only Structure Mapping + Crawler Automation

### Goal
Enable crawlers to extract data deterministically using CSS selectors learned by AI, falling back to AI only for uncertain pages. Result: 95% of work is rule-based, 5% uses AI.

### Implementation Plan (3 Days)

### Day 1: Enhance Prompt + Create AutomatedCrawler

#### Task 1.1: Update STRUCTURE_ANALYZER_PROMPT
File: `app/crawler/site_structure_analyzer.py`

Enhance the STRUCTURE_ANALYZER_PROMPT to return not just crawl_targets, but also:
- `extraction_rules` - CSS selectors for each page type
- `css_selectors` - Map of field names to CSS selectors
- `regex_patterns` - Regex patterns for text extraction
- `ai_fallback_rules` - When to use AI (if CSS fails)

Example addition to prompt:
"Return extraction_rules with css_selectors like:
  'artist_profile': {
    'css_selectors': {
      'name': 'h1.artist-name',
      'bio': 'div.biography',
      'mediums': 'ul.mediums li'
    },
    'ai_fallback_rules': 'Use AI only if CSS selectors fail'
  }"

Time: 1 hour

#### Task 1.2: Create AutomatedCrawler Class
File: `app/crawler/automated_crawler.py` (NEW)

Create new file with class AutomatedCrawler:

```python
class AutomatedCrawler:
    """Execute AI-generated crawl plans using deterministic extraction."""
    
    def __init__(self, structure_map: dict, db: AsyncSession, ai_client=None):
        self.structure_map = structure_map
        self.db = db
        self.ai_client = ai_client
        self.stats = {
            "pages_crawled": 0,
            "extracted_deterministic": 0,
            "extracted_ai_fallback": 0,
            "failed": 0
        }
    
    async def execute_crawl_plan(self, source_id: str) -> dict:
        """Execute the AI-generated crawl plan."""
        # For each phase in crawl_plan:
        # - Generate URLs from patterns
        # - Fetch each URL
        # - Extract deterministically using CSS selectors
        # - Fall back to AI if CSS fails and confidence < 80%
        # - Track stats (deterministic vs AI fallback)
        
    def _extract_deterministic(self, html: str, page_type: str, url: str) -> dict:
        """Extract using CSS selectors and regex (NO AI)."""
        soup = BeautifulSoup(html, "lxml")
        rules = self.extraction_rules.get(page_type, {})
        
        extracted = {"data": {}, "confidence": 100, "method": "deterministic"}
        
        # Try CSS selectors
        for field, selector in rules.get("css_selectors", {}).items():
            try:
                element = soup.select_one(selector)
                if element:
                    extracted["data"][field] = element.get_text(strip=True)
            except:
                extracted["confidence"] -= 10
        
        # Try regex patterns
        text = soup.get_text()
        for field, pattern in rules.get("regex_patterns", {}).items():
            try:
                match = re.search(pattern, text)
                if match:
                    extracted["data"][field] = match.group(1) if match.groups() else match.group(0)
            except:
                extracted["confidence"] -= 10
        
        return extracted
    
    async def _extract_with_ai(self, html: str, page_type: str, context: str) -> dict:
        """Fallback: Extract using AI (rare, only if CSS fails)."""
        # Only called if _extract_deterministic returns confidence < 80%
        # Cost: ~10-50 API calls per 500-page source (vs 500 before)
        
    def _classify_by_url(self, url: str) -> str:
        """Classify page type by URL pattern (NO AI)."""
        # Use mining_map from structure_map
        # Match URL against patterns
        # Return page_type
```

Time: 2-3 hours

### Day 2: Pipeline Integration + Testing

#### Task 2.1: Modify run_crawl() in Pipeline
File: `app/pipeline/runner.py`

Replace current crawl logic with:

```python
async def run_crawl(self, source_id: str) -> dict:
    """Crawl using AI-generated crawl plan (0 API calls)."""
    source = await crud.get_source(self.db, source_id)
    
    if not source.structure_map:
        raise ValueError("Structure must be analyzed first via /analyze-structure")
    
    structure_map = json.loads(source.structure_map)
    
    # Use AutomatedCrawler instead of link following
    from app.crawler.automated_crawler import AutomatedCrawler
    crawler = AutomatedCrawler(structure_map, self.db, self.ai_client)
    stats = await crawler.execute_crawl_plan(source_id)
    
    logger.info("crawl_complete", source_id=source_id, **stats)
    return stats
```

Time: 30 minutes

#### Task 2.2: Add Monitoring
File: `app/pipeline/runner.py`

Track these metrics:
- `deterministic_rate` = extracted_deterministic / pages_crawled
- `ai_fallback_rate` = extracted_ai_fallback / pages_crawled
- `failure_rate` = failed / pages_crawled

Expected:
- deterministic_rate: 85-95%
- ai_fallback_rate: 5-10%
- failure_rate: 1-5%

Log as:
```python
logger.info("crawl_stats",
    deterministic_rate=deterministic_rate,
    ai_fallback_rate=ai_fallback_rate,
    failure_rate=failure_rate,
    tokens_used=tokens_used,
    cost=cost)
```

Time: 1 hour

#### Task 2.3: Write Tests
File: `tests/test_crawler.py` (add to existing)

Add tests for:
1. `test_extract_deterministic_css()` - CSS selector extraction
2. `test_extract_deterministic_regex()` - Regex extraction
3. `test_extract_with_fallback()` - Fallback to AI
4. `test_classify_by_url()` - URL pattern classification
5. `test_crawl_plan_execution()` - Full flow

Time: 2-3 hours

#### Task 2.4: Manual Testing
1. Deploy to staging
2. Create 5-10 test sources
3. Run mining with AutomatedCrawler
4. Verify:
   - deterministic_rate > 90%
   - ai_fallback_rate < 10%
   - accuracy > 95% (compared to Phase 1)
   - tokens < 111K per source
   - speed < 450s per source

Time: 1-2 hours

### Day 3: Verification + Deployment

#### Task 3.1: Final Testing
- Run full test suite
- Verify all metrics
- Check for errors in logs

Time: 1 hour

#### Task 3.2: Code Review & Merge
- Review all changes
- Run linter/formatter
- Create PR with metrics
- Merge to main

Time: 1 hour

#### Task 3.3: Deployment
- Deploy to staging (1 day monitoring)
- Deploy to production
- Monitor metrics

Time: 1-2 hours

---

## Expected Results After Phase 2

### Token Usage
- Before Phase 2: 202,000 tokens/source
- After Phase 2: 111,000 tokens/source
- Savings: 45% reduction (vs Phase 1)
- Total: 73.6% reduction (vs baseline)

### Cost
- Before Phase 2: $2.51/source
- After Phase 2: $1.33/source
- Monthly savings (500 sources): +$590
- Annual savings: +$7,080

### Speed
- Before Phase 2: 1200s per source
- After Phase 2: 450s per source
- Improvement: 75% faster

### Quality
- Deterministic extraction: 90-95%
- AI fallback: 5-10%
- Accuracy: >95% (no regression)

---

## Key Implementation Details

### CSS Selector Extraction (NO AI)
1. Parse HTML with BeautifulSoup
2. Use CSS selectors from extraction_rules
3. Extract text content
4. Track confidence (100% if all selectors work, -10 per failure)

### Regex Extraction (NO AI)
1. Extract full text from HTML
2. Use regex patterns from extraction_rules
3. Match and capture groups
4. Track confidence

### AI Fallback (RARE)
1. Only called if deterministic confidence < 80%
2. Uses AI context hint: "This is an artist_profile"
3. Cost: ~10-50 API calls per 500-page source (vs 500 before)
4. Result: 95% cost reduction vs "AI for everything"

### Configuration
Add to `app/config.py`:
```python
USE_DETERMINISTIC_EXTRACTION = True
DETERMINISTIC_CONFIDENCE_THRESHOLD = 80
MAX_AI_FALLBACK_PER_SOURCE = 50
CRAWLER_BATCH_SIZE = 10
CRAWLER_RATE_LIMIT_MS = 1000
CRAWLER_USE_AI_FALLBACK = True
```

---

## Success Criteria

✓ Deterministic extraction > 90%
✓ AI fallback < 10%
✓ Token reduction > 40% (vs Phase 1)
✓ Accuracy maintained > 95%
✓ All tests pass
✓ Metrics logged correctly
✓ No regressions from Phase 1

---

## Rollout Strategy

Week 1: Deploy to staging
- Enable for 10-20 test sources
- Monitor deterministic_rate
- Verify accuracy

Week 2: Canary deployment
- Deploy to production
- Enable for 10% of sources
- Monitor for 24 hours

Week 3: Full rollout
- Increase to 50%
- Increase to 100%
- Monitor metrics continuously

---

## Important Notes

1. **Backward Compatible**: If structure_map missing, falls back to Phase 1 logic
2. **Graceful Fallback**: If CSS fails, tries regex, then AI if available
3. **Monitoring**: Track deterministic_rate, ai_fallback_rate, failure_rate
4. **Configuration**: Can disable AI fallback to require manual review
5. **Confidence Threshold**: Tune 80% threshold based on results

---

## Files to Create/Modify

| File | Action | Size | Priority |
|------|--------|------|----------|
| `site_structure_analyzer.py` | Modify | +50 lines | HIGH |
| `automated_crawler.py` | Create | ~300 lines | HIGH |
| `runner.py` | Modify | ±20 lines | HIGH |
| `test_crawler.py` | Add | ~80 lines | MEDIUM |
| `config.py` | Add | +10 lines | MEDIUM |

Total: ~460 lines

---

## Commit Message

```
feat: phase 2 - AI-only structure mapping with deterministic extraction

- Enhanced STRUCTURE_ANALYZER_PROMPT to return CSS selectors and extraction rules
- Created AutomatedCrawler class for deterministic extraction (90%+)
- AI fallback only for uncertain pages (5-10%)
- Result: 45% additional token reduction (73.6% total)
- Cost: $2.51 → $1.33 per source
- Speed: 1200s → 450s per source (75% faster)

BREAKING CHANGE: None (fully backward compatible)
```

---

## Questions Before Starting?

This prompt includes everything needed to implement Phase 2. Start with Day 1, Task 1.1 and proceed in order. Each task builds on the previous one.

**Ready?** Implement Phase 2 following the 3-day plan above.
```

---

## After Codex Finishes

Post-implementation checklist:
1. ✅ All code committed to feature/phase2-ai-only branch
2. ✅ All tests pass
3. ✅ No compilation errors
4. ✅ Metrics logged correctly
5. ✅ PR created with results
6. ✅ Ready for staging deployment

EOF
