# Quick Start: Structure-First Mining

## The Idea (30 seconds)

1. **User adds URL** → System analyzes it once → Saves the structure
2. **System knows** → Where the A-Z directories are, what data is where
3. **Crawlbot uses map** → Generates precise URLs, no guessing
4. **Extraction uses context** → AI knows what to look for, uses 50% fewer tokens
5. **Result** → 52% fewer tokens, structure reused forever

---

## Implementation (Code Level)

### Step 1: Database (5 minutes)
Add 4 columns to `sources` table:
```sql
ALTER TABLE sources ADD COLUMN structure_map TEXT;
ALTER TABLE sources ADD COLUMN structure_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE sources ADD COLUMN structure_error TEXT;
ALTER TABLE sources ADD COLUMN analyzed_at TIMESTAMP;
```

### Step 2: New Module (50 lines)
Create `app/crawler/site_structure_analyzer.py`:
- Takes: URL + homepage HTML
- Does: Call GPT-4o once
- Returns: {crawl_targets, mining_map, directory_structure}

### Step 3: New API Endpoint (40 lines)
Add to `app/api/routes/sources.py`:
```python
POST /sources/{id}/analyze-structure
→ Calls site_structure_analyzer
→ Saves result to database
→ Returns structure to user
```

### Step 4: Use in Crawlbot (50 lines)
Modify `app/crawler/link_follower.py`:
```python
def crawl_source():
    structure = load_saved_structure()
    for target in structure["crawl_targets"]:
        urls = generate_urls_from_pattern(target["url_pattern"])
        for url in urls:
            fetch(url)
```

### Step 5: Use in Extraction (60 lines)
Modify `app/pipeline/runner.py`:
```python
def run_extract():
    structure = load_saved_structure()
    mining_map = structure["mining_map"]
    
    for page in pages:
        page_type = find_type_in_mining_map(page.url)
        expected_fields = mining_map[page_type]["expected_fields"]
        extracted = extract(page.html, hint=expected_fields)
```

---

## User Experience

### First Time (Structure Analysis)
```
User:
  1. Paste URL: https://art.co.za
  2. Click "Add Source"
  3. Click "Analyze Structure"
  4. Wait 5 seconds
  5. See: "Found Artist A-Z directory, 26 pages"

Behind scenes:
  - 1 API call to GPT-4o
  - 2000 tokens used
  - Structure saved to database
  - $0.015 cost (one time!)
```

### Next Time (Mining)
```
User:
  1. Click "Start Mining"
  2. Wait for crawling + extraction
  3. Done!

Behind scenes:
  - 0 API calls for classification (URL pattern matching)
  - ~500 API calls for extraction (50% fewer tokens each)
  - Uses saved structure
  - $2.50 cost (52% reduction from $5.11!)
```

---

## Token Comparison

### Before (Wasteful)
```
Analyze once: 1,000 tokens
Classify 100 pages: 20,000 tokens (100 AI calls)
Extract 500 pages: 400,000 tokens (500 AI calls)
─────────────────────────────────
TOTAL: 421,000 tokens = $5.11 per source
```

### After (Optimized)
```
Analyze once: 2,000 tokens (SAVED FOREVER)
Classify 100 pages: 0 tokens (pattern matching, no AI!)
Extract 500 pages: 200,000 tokens (50% reduction, better hints)
─────────────────────────────────
TOTAL: 202,000 tokens = $2.51 per source (52% reduction!)
```

---

## Files to Create/Modify

| File | Type | Size | What |
|------|------|------|------|
| `app/crawler/site_structure_analyzer.py` | NEW | 50 lines | Structure analysis |
| `app/api/routes/sources.py` | MODIFY | +40 lines | API endpoint |
| `app/crawler/link_follower.py` | MODIFY | +50 lines | Use structure in crawl |
| `app/pipeline/runner.py` | MODIFY | +60 lines | Use structure in extract |
| `app/ai/extractors/base.py` | MODIFY | +5 lines | Accept context param |
| Migration | NEW | 10 lines | Add DB columns |

**Total code**: ~215 lines new/modified
**Total effort**: 2-3 days for one engineer

---

## Testing

```python
# 1. Test structure analysis
def test_analyze_structure():
    html = load_test_homepage()
    result = await analyze_structure(url, html, ai_client)
    assert "crawl_targets" in result
    assert "mining_map" in result

# 2. Test URL generation
def test_generate_urls():
    pattern = "/artists/[letter]"
    urls = generate_urls_from_pattern(pattern)
    assert urls == ["/artists/a", "/artists/b", ..., "/artists/z"]

# 3. Test crawl with structure
def test_crawl_with_structure():
    # Should crawl using generated URLs, not links
    
# 4. Test extraction with context
def test_extract_with_context():
    # Should use fewer tokens with context hint
    
# 5. Benchmark token usage
def test_token_reduction():
    # Measure before/after
    assert new_tokens < old_tokens * 0.55
```

---

## Deployment Checklist

- [ ] Database migration runs
- [ ] New module works in isolation
- [ ] API endpoint tested locally
- [ ] Crawlbot uses structure correctly
- [ ] Extraction produces same accuracy
- [ ] Token usage reduced to <202K per source
- [ ] Stage deployment passes all tests
- [ ] Production rollout (no downtime needed)

---

## Rollback (if needed)

```bash
# Drop the columns
ALTER TABLE sources DROP COLUMN structure_map;
ALTER TABLE sources DROP COLUMN structure_status;
ALTER TABLE sources DROP COLUMN structure_error;
ALTER TABLE sources DROP COLUMN analyzed_at;

# Restart crawlbot (uses old logic)
# Done!
```

---

## Frequently Asked Questions

**Q: What if the structure analysis fails?**
A: Falls back to old method (link following). Status="failed" is logged.

**Q: Can users override the structure?**
A: Yes, could add a manual edit form later. For now, re-run analyze-structure.

**Q: Does this work for all websites?**
A: Best for sites with A-Z directories, letter-based pagination. Falls back for others.

**Q: What about dynamic sites with JavaScript?**
A: Playwright already used. Same as before. Structure analysis works on server-rendered HTML.

**Q: Can we cache across multiple users?**
A: Yes! Same URL = same structure. Could implement shared cache layer.

---

## Success Criteria

✅ Token usage reduced by 50%+
✅ Cost reduced by 50%+
✅ Crawlbot generates correct URLs
✅ No regression in extraction accuracy
✅ All tests passing

---

## Timeline

- **Day 1**: Database + module + endpoint
- **Day 2**: Integration with crawlbot + extraction
- **Day 3**: Testing + benchmarking + deployment

---

## Money Impact

- **Cost per source BEFORE**: $5.11
- **Cost per source AFTER**: $2.51
- **Monthly savings** (500 sources): $1,300
- **Annual savings**: $15,600
- **Implementation cost**: ~$3,000 (3 engineer days)
- **ROI**: Break-even in 3 months

---

**Ready to build?** Start with `STRUCTURE_FIRST_IMPLEMENTATION.md` for full code examples.
