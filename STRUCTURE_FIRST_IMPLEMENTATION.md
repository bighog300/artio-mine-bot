# Structure-First Mining: Implementation Guide

## What You're Building

```
User Input Flow:
┌─────────────────────────┐
│ 1. User adds URL        │  POST /sources {"url": "https://art.co.za"}
└────────────┬────────────┘
             ↓
┌─────────────────────────────────────────────┐
│ 2. System analyzes structure (CACHED)        │
│    - Fetch homepage                         │
│    - Detect A-Z directory patterns          │
│    - Map crawl targets                      │
│    - Save to database                       │
└────────────┬────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────┐
│ 3. Return structure map to UI               │
│    {                                        │
│      crawl_targets: [                       │
│        {section: "Artist A-Z",              │
│         url: "/artists",                    │
│         pattern: "/artists/[letter]",       │
│         pagination: "letter"}               │
│      ],                                     │
│      mining_map: {                          │
│        artist_profile: {                    │
│          pattern: "/artists/[l]/[name]",    │
│          fields: ["bio","mediums","contact"]│
│        }                                    │
│      }                                      │
│    }                                        │
└────────────┬────────────────────────────────┘
             ↓
┌─────────────────────────┐
│ 4. Crawlbot uses map    │
│    - Generate URLs      │
│    - Fetch pages        │
│    - Know exactly       │
│      where data is      │
└─────────────────────────┘
```

---

## Step 1: Database Schema (Add 4 Columns)

```sql
-- Migration: app/db/migrations/versions/xxxx_add_structure_to_sources.py

ALTER TABLE sources ADD COLUMN structure_map TEXT;
-- JSON structure analysis result

ALTER TABLE sources ADD COLUMN structure_status VARCHAR(50) DEFAULT 'pending';
-- pending | analyzing | analyzed | failed

ALTER TABLE sources ADD COLUMN structure_error TEXT;
-- Error message if analysis failed

ALTER TABLE sources ADD COLUMN analyzed_at TIMESTAMP;
-- When structure was last analyzed
```

---

## Step 2: Create Site Structure Analyzer

**File: `app/crawler/site_structure_analyzer.py`**

```python
"""Analyze site structure to create crawl map."""

from dataclasses import dataclass
import json
import structlog
from app.ai.client import OpenAIClient

logger = structlog.get_logger()

STRUCTURE_ANALYZER_PROMPT = """Analyze this website to find:
1. A-Z directory structure (where artist/item listings are)
2. Pagination patterns (letter-based, numbered, etc.)
3. Nested structure (detail pages under listings)
4. Data locations (where to find bio, contact, images, etc.)

Return ONLY JSON:
{
  "crawl_targets": [
    {
      "section_name": "Artist A-Z",
      "base_url": "/artists",
      "pagination_type": "letter",
      "url_pattern": "/artists/[letter]",
      "estimated_pages": 26,
      "expected_content": "artist directory listing"
    }
  ],
  "mining_map": {
    "artist_profile": {
      "url_pattern": "/artists/[letter]/[name]",
      "parent_pattern": "/artists/[letter]",
      "expected_fields": ["name", "bio", "mediums", "contact", "website"]
    },
    "artwork_listing": {
      "url_pattern": "/artists/[letter]/[name]/works",
      "parent_pattern": "/artists/[letter]/[name]",
      "expected_fields": ["title", "medium", "year", "price"]
    }
  },
  "directory_structure": "Artist A-Z directory with nested profile pages",
  "confidence": 95
}"""

@dataclass
class CrawlTarget:
    section_name: str
    base_url: str
    pagination_type: str  # "letter", "numbered", "none"
    url_pattern: str       # "/artists/[letter]"
    estimated_pages: int
    expected_content: str

async def analyze_structure(
    url: str,
    html: str,
    ai_client: OpenAIClient,
) -> dict:
    """
    One-time analysis of site structure.
    Returns map for crawlbot to use forever.
    """
    
    # Prepare input
    nav_section = _extract_nav_html(html)[:2000]
    
    user_content = f"""Homepage: {url}

Navigation:
{nav_section}

HTML (first 3000 chars):
{html[:3000]}"""

    try:
        # Call OpenAI once to analyze structure
        response = await ai_client.complete(
            system_prompt=STRUCTURE_ANALYZER_PROMPT,
            user_content=user_content,
            response_format={"type": "json_object"},
        )
        
        logger.info(
            "structure_analysis_complete",
            url=url,
            confidence=response.get("confidence", 0),
            targets=len(response.get("crawl_targets", [])),
        )
        
        return response
        
    except Exception as exc:
        logger.error("structure_analysis_failed", url=url, error=str(exc))
        raise

def _extract_nav_html(html: str) -> str:
    """Extract just nav/header HTML."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    nav_html = []
    for tag in soup.find_all(["nav", "header"]):
        nav_html.append(str(tag)[:1000])
    return "\n".join(nav_html)
```

---

## Step 3: API Endpoint (Save Structure)

**File: `app/api/routes/sources.py`** - Add endpoint:

```python
@router.post("/{source_id}/analyze-structure", response_model=dict)
async def analyze_source_structure(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    """
    Analyze source structure ONCE and save forever.
    Crawlbot will use this map to know where to fetch data.
    """
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Check if already analyzed
    if source.structure_map and source.structure_status == "analyzed":
        return {
            "source_id": source_id,
            "status": "cached",
            "structure": json.loads(source.structure_map),
        }
    
    # Mark as analyzing
    await crud.update_source(db, source_id, structure_status="analyzing")
    
    try:
        # Fetch homepage
        from app.crawler.fetcher import fetch
        from app.crawler.site_structure_analyzer import analyze_structure
        
        result = await fetch(source.url)
        if not result.html:
            raise ValueError("Could not fetch homepage HTML")
        
        # Analyze structure (ONE AI CALL)
        ai_client = OpenAIClient()
        structure = await analyze_structure(
            url=source.url,
            html=result.html,
            ai_client=ai_client,
        )
        
        # Save to database
        await crud.update_source(
            db,
            source_id,
            structure_map=json.dumps(structure),
            structure_status="analyzed",
            analyzed_at=datetime.now(UTC),
        )
        
        return {
            "source_id": source_id,
            "status": "analyzed",
            "structure": structure,
        }
        
    except Exception as exc:
        logger.error("structure_analysis_failed", source_id=source_id, error=str(exc))
        await crud.update_source(
            db,
            source_id,
            structure_status="failed",
            structure_error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))
```

---

## Step 4: Crawlbot Uses Saved Structure

**File: `app/crawler/link_follower.py`** - Modify crawl_source:

```python
async def crawl_source(
    source_id: str,
    site_map: SiteMap,
    db: AsyncSession,
    robots_checker: RobotsChecker,
) -> CrawlStats:
    """
    Crawl using saved structure map.
    Generate URLs from patterns instead of following links.
    """
    
    # Load saved structure
    source = await crud.get_source(db, source_id)
    structure = None
    if source and source.structure_map:
        structure = json.loads(source.structure_map)
    
    stats = CrawlStats()
    
    if structure:
        # USE SAVED STRUCTURE - Much faster and more precise
        logger.info("crawl_using_structure", source_id=source_id)
        
        # Generate URLs from patterns
        crawl_targets = structure.get("crawl_targets", [])
        
        for target in crawl_targets:
            # Example: pattern="/artists/[letter]" → generate /artists/a through /artists/z
            pattern = target.get("url_pattern", "")
            generated_urls = _generate_urls_from_pattern(
                base_url=source.url,
                pattern=pattern,
                pagination_type=target.get("pagination_type"),
            )
            
            # Crawl generated URLs
            for url in generated_urls:
                try:
                    result = await fetch(url)
                    if result.html:
                        page = await crud.create_page(
                            db,
                            source_id=source_id,
                            url=url,
                            html=result.html,
                            status="fetched",
                        )
                        stats.pages_fetched += 1
                except Exception as exc:
                    logger.error("fetch_failed", url=url, error=str(exc))
                    stats.pages_error += 1
    else:
        # FALLBACK - old method, follow links from site map
        logger.info("crawl_using_sitemap_fallback", source_id=source_id)
        # ... existing crawl logic
    
    return stats


def _generate_urls_from_pattern(
    base_url: str,
    pattern: str,
    pagination_type: str,
) -> list[str]:
    """Generate concrete URLs from pattern."""
    from urllib.parse import urljoin
    
    urls = []
    
    if pagination_type == "letter":
        # /artists/[letter] → /artists/a, /artists/b, ..., /artists/z
        for letter in "abcdefghijklmnopqrstuvwxyz":
            url = pattern.replace("[letter]", letter)
            urls.append(urljoin(base_url, url))
    
    elif pagination_type == "numbered":
        # /artists?page=[page] → /artists?page=1 through page=50
        for page in range(1, 51):  # Adjust as needed
            url = pattern.replace("[page]", str(page))
            urls.append(urljoin(base_url, url))
    
    else:
        # No pagination, just one URL
        urls.append(urljoin(base_url, pattern))
    
    return urls
```

---

## Step 5: Pipeline Knows Expected Data

**File: `app/pipeline/runner.py`** - Update extraction:

```python
async def run_extract(self, source_id: str) -> ExtractionStats:
    """Extract using structure hints."""
    
    # Load structure analysis
    source = await crud.get_source(self.db, source_id)
    structure = None
    if source and source.structure_map:
        structure = json.loads(source.structure_map)
    
    logger.info("extraction_started", source_id=source_id)
    
    pages = await crud.list_pages_by_statuses(
        self.db,
        source_id=source_id,
        statuses=["fetched"],
    )
    
    stats = ExtractionStats()
    mining_map = structure.get("mining_map", {}) if structure else {}
    
    for page in pages:
        # Find expected data type from mining_map
        page_type = None
        expected_fields = []
        
        for data_type, pattern_info in mining_map.items():
            url_pattern = pattern_info.get("url_pattern", "")
            if _matches_pattern(page.url, url_pattern):
                page_type = data_type
                expected_fields = pattern_info.get("expected_fields", [])
                break
        
        if not page_type:
            # Fallback to classification
            page_type = await classify_page(page.url, page.html, self.ai_client)
            expected_fields = []
        
        # Extract with structure context
        extractor = self._extractors.get(page_type)
        if not extractor:
            continue
        
        try:
            # Tell extractor what fields to look for
            context = f"Expected fields: {', '.join(expected_fields)}\n\n" if expected_fields else ""
            
            extracted = await extractor.extract(page.html, context=context)
            
            # Create record
            await crud.create_record(
                self.db,
                source_id=source_id,
                page_id=page.id,
                record_type=page_type,
                title=extracted.get("name") or extracted.get("title"),
                description=extracted.get("bio") or extracted.get("description"),
                raw_data=json.dumps(extracted),
            )
            stats.records_created += 1
            
        except Exception as exc:
            logger.error("extraction_failed", page_id=page.id, error=str(exc))
            stats.records_failed += 1
    
    return stats


def _matches_pattern(url: str, pattern: str) -> bool:
    """Match URL against pattern."""
    import re
    regex = pattern
    regex = regex.replace("[letter]", "[a-z]")
    regex = regex.replace("[name]", "[a-z0-9-]+")
    regex = regex.replace("[page]", r"\d+")
    try:
        return bool(re.search(regex, url, re.IGNORECASE))
    except:
        return False
```

---

## Step 6: User Workflow

### For End Users:

```
1. User goes to UI
   → "Add Source"
   → Paste URL: https://art.co.za
   → Click "Add"

2. Button appears: "Analyze Structure"
   → Click it
   → Shows: "Analyzing... found Artist A-Z directory, 26 pages"
   → Shows structure map for review

3. Button changes: "Start Mining"
   → Click it
   → System crawls using structure
   → Extracts data using structure context
   → Done!

Next time:
   → Just "Start Mining" (structure reused)
   → Much faster (no re-analysis)
```

### API Calls:

```
Step 1: Create source
POST /sources
{
  "url": "https://art.co.za",
  "name": "Art Co ZA"
}
→ Response: {source_id: "abc123", status: "pending"}

Step 2: Analyze structure (ONE TIME)
POST /sources/abc123/analyze-structure
→ Response: {
    status: "analyzed",
    structure: {
      crawl_targets: [...],
      mining_map: {...},
      directory_structure: "Artist A-Z...",
      confidence: 95
    }
  }

Step 3: Start mining (USES SAVED STRUCTURE)
POST /mine/abc123/start
→ Job queued, crawls using structure
→ Extracts using structure hints
→ Done!
```

---

## Token Savings

**Before** (without structure):
```
Analyze structure: 1000 tokens
Classify 100 pages: 20,000 tokens (100 × $0.001)
Extract 500 pages: 400,000 tokens (500 × $0.01)
─────────────────────────────────
TOTAL: 421,000 tokens = $5.11
```

**After** (with structure):
```
Analyze structure: 2000 tokens (ONE TIME, saved forever)
Classify using patterns: 0 tokens (URL matching, no AI)
Extract with hints: 200,000 tokens (50% reduction)
─────────────────────────────────
TOTAL: 202,000 tokens = $2.51 (52% reduction!)
```

---

## Implementation Checklist

- [ ] Add 4 columns to sources table (migration)
- [ ] Create `site_structure_analyzer.py`
- [ ] Add `analyze-structure` API endpoint
- [ ] Modify crawl_source to use structure
- [ ] Modify extraction to use structure context
- [ ] Update extractors to accept context
- [ ] Test structure analysis accuracy
- [ ] Test crawlbot with generated URLs
- [ ] Test extraction with context
- [ ] Benchmark token usage
- [ ] Deploy

---

## Files to Create/Modify

**New Files:**
- `app/crawler/site_structure_analyzer.py` (50 lines)

**Modified Files:**
- `app/api/routes/sources.py` (add 1 endpoint, 40 lines)
- `app/crawler/link_follower.py` (modify crawl_source, 50 lines)
- `app/pipeline/runner.py` (modify extraction, 60 lines)
- `app/ai/extractors/base.py` (add context param, 5 lines)

**Database:**
- Migration: add 4 columns to sources table

---

## Example Structure Response

```json
{
  "crawl_targets": [
    {
      "section_name": "Artist A-Z",
      "base_url": "/artists",
      "pagination_type": "letter",
      "url_pattern": "/artists/[letter]",
      "estimated_pages": 26,
      "expected_content": "Directory of artists indexed by first letter"
    },
    {
      "section_name": "Artist Profiles",
      "base_url": "/artists/a",
      "pagination_type": "none",
      "url_pattern": "/artists/[letter]/[artist-name]",
      "estimated_pages": 500,
      "expected_content": "Individual artist profile pages"
    }
  ],
  "mining_map": {
    "artist_directory": {
      "url_pattern": "/artists/[a-z]$",
      "expected_fields": ["artist_names", "links_to_profiles"]
    },
    "artist_profile": {
      "url_pattern": "/artists/[a-z]/[a-z0-9-]+$",
      "parent_pattern": "/artists/[a-z]",
      "expected_fields": ["name", "bio", "birth_year", "mediums", "website", "contact"]
    }
  },
  "directory_structure": "A-Z artist directory with nested profile pages under each letter",
  "confidence": 95
}
```

---

## One-Time vs Repeated

**One-Time (Expensive):**
- Analyze structure (1-2 API calls, 2000 tokens)
- Done once, saved forever
- Cost: ~$0.015

**Repeated (Cheap):**
- Classify by URL pattern (0 API calls)
- Extract with context (1 API call per page, 50% fewer tokens)
- Cost: ~$2.50 for 500 pages

**Result:** 52% token reduction, reuse structure forever!

