# WEEK 1 IMPLEMENTATION BUNDLE
## Smart Mode Foundation - OpenAI Integration & Core Services

**Branch:** `feature/smart-mode`  
**Duration:** 5 days (40 hours)  
**Goal:** Complete backend foundation with OpenAI API integration

---

## DELIVERABLES CHECKLIST

- [ ] OpenAI client wrapper with JSON mode
- [ ] Site analyzer service (detects site type, CMS, entities)
- [ ] Config generator service (creates mining configs via GPT-4o)
- [ ] Smart miner orchestrator (end-to-end workflow)
- [ ] Quality assurance module (test configs, refine failures)
- [ ] Validation and error handling
- [ ] Integration tests passing
- [ ] Documentation complete

---

## FILE STRUCTURE TO CREATE

```
app/
├── ai/
│   ├── __init__.py
│   ├── openai_client.py        # OpenAI API wrapper
│   ├── site_analyzer.py        # Site type detection
│   ├── config_generator.py     # Config generation via GPT-4o
│   ├── smart_miner.py          # Main orchestrator
│   ├── quality_assurance.py    # Test & refinement
│   └── models.py               # Pydantic models
└── config.py                   # Add OpenAI settings

tests/
├── test_ai_openai_client.py
├── test_ai_site_analyzer.py
├── test_ai_config_generator.py
├── test_ai_smart_miner.py
└── test_ai_quality_assurance.py
```

---

## ENVIRONMENT SETUP

Add to `.env`:
```bash
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL_CONFIG=gpt-4o
OPENAI_MODEL_ANALYSIS=gpt-3.5-turbo
SMART_MINE_MAX_REFINEMENTS=2
SMART_MINE_TEST_PAGES=10
SMART_MINE_SUCCESS_THRESHOLD=0.85
```

Add to `requirements.txt`:
```
openai==1.12.0
```

---

## IMPLEMENTATION DETAILS

### 1. OpenAI Client Wrapper

**File:** `app/ai/openai_client.py`

**Requirements:**
- Async client initialization
- JSON mode support (use `response_format={"type": "json_object"}`)
- Retry logic (max 3 attempts with exponential backoff)
- Error handling for rate limits, invalid JSON, API errors
- Token usage tracking
- Temperature control (default 0.7 for config, 0.3 for analysis)
- Model selection (support both GPT-4o and GPT-3.5)

**Key Methods:**
```python
async def generate_json(
    system_prompt: str,
    user_prompt: str,
    model: str = None,
    temperature: float = 0.7,
) -> dict
```

**Error Handling:**
- Catch `json.JSONDecodeError` → raise `ValueError`
- Catch `openai.RateLimitError` → retry with backoff
- Catch `openai.APIError` → raise `RuntimeError`
- Log all API calls with token counts

---

### 2. Site Analyzer

**File:** `app/ai/site_analyzer.py`

**Requirements:**
- Fetch homepage HTML (use existing `app.crawler.fetcher.fetch`)
- Discover 5 sample pages from homepage links
- Analyze with GPT-3.5-turbo (cheaper, faster)
- Return structured analysis

**Output Schema:**
```python
class SiteAnalysis(TypedDict):
    site_type: str          # "art_gallery" | "event_calendar" | "directory"
    cms: str                # "wordpress" | "squarespace" | "custom"
    entity_types: list[str] # ["artists", "events", "venues"]
    url_patterns: dict      # {"artists": "/artists/[slug]"}
    confidence: float       # 0.0 - 1.0
```

**Prompt Strategy:**
- System: Brief expert identity
- User: URL + homepage HTML (first 3000 chars) + sample URLs
- Temperature: 0.3 (consistency)
- Model: gpt-3.5-turbo (cost-effective)

**Sample Discovery:**
- Parse homepage HTML with BeautifulSoup
- Extract internal links (same domain)
- Filter out nav/footer links
- Return up to 5 diverse samples

---

### 3. Config Generator

**File:** `app/ai/config_generator.py`

**Requirements:**
- Generate complete mining configuration
- Use GPT-4o for quality
- Fetch sample pages for each entity type
- Include detailed system prompt with rules
- Validate output against JSON schema

**System Prompt Rules:**
1. Identifiers MUST be specific regex (not `/` or `.*`)
2. CSS selectors prefer classes over tags
3. Required fields must be reliably extractable
4. Use fallback selectors (e.g., `h1.title, h1, h2`)
5. Follow rules must be precise
6. Output ONLY valid JSON

**User Prompt Components:**
- Site URL
- Site analysis results
- Homepage HTML (5000 chars)
- Sample page HTMLs per entity type (3000 chars each)
- URL patterns detected

**Output Schema:**
```python
{
  "crawl_plan": {
    "phases": [...]
  },
  "extraction_rules": {
    "page_type_key": {
      "identifiers": ["regex"],
      "css_selectors": {"field": "selector"}
    }
  },
  "page_type_rules": {...},
  "record_type_rules": {...},
  "follow_rules": {...},
  "asset_rules": {...}
}
```

**Validation:**
- Check identifiers not too broad (not `/`, `.*`, `/.*`)
- Ensure at least 1 crawl phase
- Ensure at least 1 extraction rule
- Validate against JSON schema
- Set base_url for all phases

---

### 4. Smart Miner Orchestrator

**File:** `app/ai/smart_miner.py`

**Requirements:**
- Orchestrate full workflow
- Update source status at each stage
- Handle errors gracefully
- Support template loading (stub for now)
- Log all steps

**Workflow Steps:**
1. Analyze site (update status: "analyzing")
2. Check for template match (stub - always returns None for now)
3. Generate config if no template (update status: "generating_config")
4. Test config on 10 pages (update status: "testing")
5. Refine if success_rate < 85% (max 2 attempts, update status: "refining")
6. Save config to source.structure_map
7. Start mining (update status: "mining")

**Status Updates:**
- Use `crud.update_source()` to set status and error_message
- Commit after each status change
- Log each transition

**Error Handling:**
- Try-catch entire workflow
- Set status="error" and error_message on failure
- Re-raise exception after cleanup

---

### 5. Quality Assurance

**File:** `app/ai/quality_assurance.py`

**Requirements:**
- Test configuration on small sample
- Analyze test results
- Refine configuration if needed

**Test Config Function:**
- Create temporary test source
- Run mini crawl (max 10 pages)
- Use `AutomatedCrawler` with `ai_allowed=False`
- Count: pages, classifications, records created
- Identify failures (unknown pages, extraction failures)
- Delete test source after
- Return success_rate and failure details

**Refine Config Function:**
- Take original config + test failures
- Use GPT-4o to fix issues
- System prompt: "Fix broken config based on failures"
- User prompt: Original config + failure details
- Return fixed config

**Failure Analysis:**
- Page classified as "unknown" → identifier too narrow
- Extraction failed → selector not finding elements
- Missing required field → selector returned empty

---

### 6. Config Settings

**File:** `app/config.py`

**Add to Settings class:**
```python
# OpenAI
openai_api_key: str = Field(..., env="OPENAI_API_KEY")
openai_model_config: str = Field(default="gpt-4o", env="OPENAI_MODEL_CONFIG")
openai_model_analysis: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL_ANALYSIS")
openai_max_retries: int = Field(default=3, env="OPENAI_MAX_RETRIES")
openai_timeout: int = Field(default=60, env="OPENAI_TIMEOUT")

# Smart Mining
smart_mine_max_refinements: int = Field(default=2)
smart_mine_test_pages: int = Field(default=10)
smart_mine_success_threshold: float = Field(default=0.85)
smart_mine_cost_cap_per_url: float = Field(default=0.50)
```

---

## TESTING REQUIREMENTS

### Unit Tests

**test_ai_openai_client.py:**
- Test successful JSON generation
- Test retry on rate limit
- Test error handling (invalid JSON, API error)
- Test model selection
- Test temperature control

**test_ai_site_analyzer.py:**
- Test analysis of known art gallery
- Test detection of WordPress
- Test confidence scores
- Test with missing HTML
- Test sample discovery

**test_ai_config_generator.py:**
- Test config generation for art gallery
- Test validation rejects broad identifiers
- Test all required sections present
- Test selector specificity
- Test fallback selectors included

**test_ai_smart_miner.py:**
- Test full workflow (analyze → generate → test → save)
- Test refinement loop (low success triggers refine)
- Test max refinement limit (stops after 2 attempts)
- Test error handling (sets status="error")
- Test status updates at each stage

**test_ai_quality_assurance.py:**
- Test config testing on 10 pages
- Test success_rate calculation
- Test failure identification
- Test config refinement
- Test cleanup (test source deleted)

### Integration Tests

Create `tests/test_integration_smart_mine.py`:
- Full end-to-end test with real URL (use test fixture)
- Mock OpenAI responses to avoid API costs
- Verify source created → config generated → test passed → mining started
- Check all database records created correctly

---

## LOGGING & MONITORING

Use `structlog` for structured logging:

```python
logger.info(
    "smart_mine_started",
    source_id=source_id,
    url=url,
)

logger.info(
    "site_analyzed",
    site_type=analysis["site_type"],
    entity_types=analysis["entity_types"],
    confidence=analysis["confidence"],
)

logger.info(
    "config_generated",
    phases_count=len(config["crawl_plan"]["phases"]),
    page_types_count=len(config["extraction_rules"]),
)

logger.info(
    "config_tested",
    success_rate=test_result["success_rate"],
    records_created=test_result["records_created"],
)
```

---

## ERROR MESSAGES (USER-FACING)

Make error messages helpful:

**Bad:**
```
"Config generation failed"
```

**Good:**
```
"Could not generate mining configuration. The site structure was too complex. 
Please try using Guided Mode or contact support."
```

**Bad:**
```
"Test failed"
```

**Good:**
```
"Test crawl found issues: 0 records created from 10 pages. The site may require 
manual configuration. Would you like to try Guided Mode?"
```

---

## VALIDATION RULES

### Identifier Validation
```python
INVALID_IDENTIFIERS = ["/", ".*", "/.*", "/.+", ""]

for page_type, rules in config["extraction_rules"].items():
    for identifier in rules.get("identifiers", []):
        if identifier in INVALID_IDENTIFIERS:
            raise ValueError(
                f"Identifier too broad in {page_type}: '{identifier}'. "
                f"Must be specific regex like '/artists/[^/]+/?$'"
            )
        if len(identifier) < 3:
            raise ValueError(f"Identifier too short: '{identifier}'")
```

### Selector Validation
```python
# Warn on overly generic selectors
GENERIC_SELECTORS = ["p", "div", "span", "a", "img"]

for page_type, rules in config["extraction_rules"].items():
    for field, selector in rules.get("css_selectors", {}).items():
        if selector in GENERIC_SELECTORS:
            logger.warning(
                "generic_selector_detected",
                page_type=page_type,
                field=field,
                selector=selector,
            )
```

---

## PERFORMANCE TARGETS

- Site analysis: < 5 seconds
- Config generation: < 15 seconds
- Config testing: < 30 seconds
- Total time to mining start: < 60 seconds

---

## COST TRACKING

Track costs per operation:

```python
class CostTracker:
    """Track OpenAI API costs."""
    
    @staticmethod
    def calculate_cost(tokens_input: int, tokens_output: int, model: str) -> float:
        """Calculate cost based on token usage."""
        rates = {
            "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
            "gpt-3.5-turbo": {"input": 0.50 / 1_000_000, "output": 1.50 / 1_000_000},
        }
        rate = rates.get(model, rates["gpt-4o"])
        return (tokens_input * rate["input"]) + (tokens_output * rate["output"])
```

Log costs:
```python
logger.info(
    "openai_api_call",
    operation="config_generation",
    model="gpt-4o",
    tokens_input=8500,
    tokens_output=2700,
    cost=0.074,
)
```

---

## COMMON PITFALLS TO AVOID

1. **Don't use OpenAI without JSON mode** - Always set `response_format={"type": "json_object"}`
2. **Don't skip validation** - Always validate generated configs before using
3. **Don't forget to clean up test sources** - Use try-finally blocks
4. **Don't log API keys** - Use `structlog.processors.add_log_level` to filter secrets
5. **Don't ignore rate limits** - Implement retry with exponential backoff
6. **Don't return raw HTML in errors** - Sanitize user-facing error messages
7. **Don't forget to commit DB changes** - Call `await db.commit()` after updates

---

## DOCUMENTATION TO CREATE

Create `docs/smart_mode_week1_architecture.md`:

```markdown
# Smart Mode Architecture - Week 1

## Overview
Smart Mode uses OpenAI GPT-4o to automatically generate mining configurations.

## Components

### OpenAI Client (`app/ai/openai_client.py`)
Wrapper for OpenAI API with retry logic and JSON mode.

### Site Analyzer (`app/ai/site_analyzer.py`)
Detects site type, CMS, and entity types using GPT-3.5-turbo.

### Config Generator (`app/ai/config_generator.py`)
Generates complete mining configs using GPT-4o.

### Smart Miner (`app/ai/smart_miner.py`)
Orchestrates the full workflow.

### Quality Assurance (`app/ai/quality_assurance.py`)
Tests configs and refines failures.

## Workflow
1. User provides URL
2. Analyze site structure
3. Generate configuration
4. Test on 10 pages
5. Refine if needed (max 2 attempts)
6. Start mining

## Cost
- Average: $0.065 per URL
- Site analysis: $0.003
- Config generation: $0.050
- Config refinement: $0.012 (if needed)
```

---

## WEEK 1 COMPLETION CRITERIA

**Must have:**
- [ ] All 5 core modules implemented
- [ ] OpenAI integration working with JSON mode
- [ ] Can generate valid config for 3 different site types
- [ ] Test crawl validates configs correctly
- [ ] Refinement loop fixes common issues
- [ ] All tests passing (>90% coverage)
- [ ] Error handling comprehensive
- [ ] Logging structured and helpful

**Success metrics:**
- Generate valid config for art.co.za: ✅
- Generate valid config for event calendar site: ✅
- Generate valid config for directory site: ✅
- Success rate on first generation: >70%
- Success rate after refinement: >85%
- Total time analysis → mining start: <60 seconds

---

## NEXT WEEK PREVIEW

Week 2 will add:
- API endpoints (`POST /api/smart-mine/`)
- Background job processing
- Template library foundation
- Real-time status tracking

---

## HANDOFF NOTES FOR WEEK 2

After Week 1 completion, provide:
1. List of any deviations from plan
2. Performance metrics (actual vs target)
3. Known issues or technical debt
4. Recommendations for Week 2
5. Updated cost analysis (actual token usage)

---

# CODEX EXECUTION PROMPT

I am working on a web scraping platform called Artio Mine Bot. I need to implement "Smart Mode" - 
an AI-powered feature that automatically generates mining configurations using OpenAI's GPT-4o.

This is **Week 1 of 8**: Foundation and Core Services.

## Your Task

Implement the complete backend foundation for Smart Mode with the following components:

1. **OpenAI Client Wrapper** (`app/ai/openai_client.py`)
   - Async OpenAI client with JSON mode
   - Retry logic with exponential backoff
   - Error handling for rate limits and API errors
   - Token usage tracking and cost calculation
   - Support for both GPT-4o and GPT-3.5-turbo

2. **Site Analyzer** (`app/ai/site_analyzer.py`)
   - Detect site type (art_gallery, event_calendar, directory, etc.)
   - Identify CMS/platform (wordpress, squarespace, custom)
   - Find entity types (artists, events, venues, exhibitions)
   - Discover URL patterns
   - Use GPT-3.5-turbo for cost efficiency
   - Return structured SiteAnalysis TypedDict

3. **Config Generator** (`app/ai/config_generator.py`)
   - Generate complete mining configuration via GPT-4o
   - Fetch sample pages for each entity type
   - Create comprehensive prompts with rules
   - Validate generated configs (reject broad identifiers like "/")
   - Return config matching existing structure_map schema

4. **Smart Miner Orchestrator** (`app/ai/smart_miner.py`)
   - Orchestrate end-to-end workflow
   - Update source status at each stage (analyzing, generating_config, testing, mining)
   - Handle template matching (stub for now - always return None)
   - Execute refinement loop (max 2 attempts)
   - Save config to source.structure_map

5. **Quality Assurance** (`app/ai/quality_assurance.py`)
   - Test configs on 10 sample pages
   - Create temporary test source
   - Run mini crawl with AutomatedCrawler
   - Calculate success rate (records created / pages crawled)
   - Refine configs using GPT-4o when success_rate < 85%
   - Clean up test sources after

6. **Configuration** (`app/config.py`)
   - Add OpenAI settings to Settings class
   - Add smart mining parameters
   - Use Pydantic Field with env variable support

7. **Comprehensive Tests**
   - Unit tests for each module
   - Integration test for full workflow
   - Mock OpenAI to avoid API costs in tests
   - Achieve >90% test coverage

## Technical Requirements

- Use existing `app.crawler.fetcher.fetch` for HTTP requests
- Use existing `app.crawler.automated_crawler.AutomatedCrawler` for test crawls
- Use existing `app.db.crud` for database operations
- Follow existing code patterns and structure
- Use `structlog` for logging
- Use BeautifulSoup for HTML parsing
- Validate all configs against JSON schema
- Handle all errors gracefully with helpful messages

## Existing Context

The repository already has:
- FastAPI backend with SQLAlchemy async ORM
- Crawler that executes structure_map configurations
- Database models for Source, Page, Record
- Existing mapping workflow (manual configuration)

Your implementation should integrate seamlessly with these existing systems.

## Validation Rules

**Identifiers must NOT be:**
- "/" (matches everything)
- ".*" or "/.*" (too broad)
- Empty or less than 3 chars

**CSS Selectors should:**
- Prefer class names over generic tags
- Include fallback options (e.g., "h1.title, h1, h2")
- Not be overly broad ("p", "div", "a" alone)

## Expected Output Structure

```python
{
  "crawl_plan": {
    "phases": [
      {
        "phase_name": "artist_detail",
        "base_url": "https://example.com",
        "url_pattern": "/artists/[a-z0-9\\-]+/?",
        "pagination_type": "follow_links",
        "num_pages": 500
      }
    ]
  },
  "extraction_rules": {
    "artist_detail": {
      "identifiers": ["/artists/[^/]+/?$"],
      "css_selectors": {
        "title": "h1.artist-name, h1",
        "description": ".artist-bio, .biography",
        "email": "a[href^='mailto:']"
      }
    }
  },
  "page_type_rules": {...},
  "record_type_rules": {...},
  "follow_rules": {...},
  "asset_rules": {...}
}
```

## Success Criteria

After implementation:
1. I can call `SmartMiner.smart_mine(source_id, url)` and it completes successfully
2. It generates a valid config for https://art.co.za
3. The config passes validation (no broad identifiers)
4. Test crawl achieves >85% success rate
5. All tests pass with >90% coverage
6. Cost per URL is tracked and logged
7. Helpful error messages on failures

## Important Notes

- Use OpenAI's JSON mode: `response_format={"type": "json_object"}`
- Always validate configs before using them
- Clean up test sources (use try-finally)
- Log all steps with structured logging
- Track and log token usage and costs
- Set source status at each stage
- Max 2 refinement attempts, then escalate to human

Please implement this complete backend foundation, ensuring all components work together 
seamlessly and all tests pass.

When complete, provide:
1. Summary of what was implemented
2. Any deviations from the specification
3. Known issues or limitations
4. Actual token usage and costs observed
5. Recommendations for Week 2

---

**Files to create/modify:**
- app/ai/__init__.py
- app/ai/openai_client.py
- app/ai/site_analyzer.py
- app/ai/config_generator.py
- app/ai/smart_miner.py
- app/ai/quality_assurance.py
- app/ai/models.py (Pydantic models)
- app/config.py (add OpenAI settings)
- requirements.txt (add openai==1.12.0)
- tests/test_ai_openai_client.py
- tests/test_ai_site_analyzer.py
- tests/test_ai_config_generator.py
- tests/test_ai_smart_miner.py
- tests/test_ai_quality_assurance.py
- tests/test_integration_smart_mine.py
- docs/smart_mode_week1_architecture.md

**Environment variables needed:**
```
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL_CONFIG=gpt-4o
OPENAI_MODEL_ANALYSIS=gpt-3.5-turbo
```

Start implementation now.
