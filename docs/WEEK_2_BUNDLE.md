# WEEK 2 IMPLEMENTATION BUNDLE
## API Endpoints, Background Jobs & Template Library

**Branch:** `feature/smart-mode`  
**Duration:** 5 days (40 hours)  
**Prerequisites:** Week 1 complete (core AI services implemented)  
**Goal:** Expose Smart Mode via API, add job processing, implement template system

---

## DELIVERABLES CHECKLIST

- [ ] API endpoints for smart mining
- [ ] Background job execution
- [ ] Template library storage and matching
- [ ] Real-time status tracking
- [ ] Initial template collection (10 templates)
- [ ] API tests passing
- [ ] Integration with frontend-ready endpoints
- [ ] Documentation complete

---

## FILE STRUCTURE TO CREATE

```
app/
├── api/
│   └── routes/
│       └── smart_mining.py         # New API routes
├── ai/
│   ├── templates.py                # Template library
│   ├── template_data/              # JSON template storage
│   │   ├── art_gallery_v1.json
│   │   ├── event_calendar_v1.json
│   │   └── ... (8 more)
│   └── cache.py                    # Caching layer
└── db/
    └── crud.py                     # Add count methods

tests/
├── test_api_smart_mining.py
├── test_ai_templates.py
└── test_ai_cache.py

scripts/
└── create_initial_templates.py     # Seed template library

docs/
└── smart_mode_week2_api.md
```

---

## IMPLEMENTATION DETAILS

### 1. API Routes

**File:** `app/api/routes/smart_mining.py`

**Endpoints to create:**

```python
POST   /api/smart-mine/              # Start smart mining
GET    /api/smart-mine/{id}/status   # Get status
POST   /api/smart-mine/{id}/retry    # Retry failed mine
GET    /api/smart-mine/templates     # List available templates
GET    /api/smart-mine/templates/{id} # Get template details
```

**Request/Response Models:**

```python
class SmartMineRequest(BaseModel):
    url: str
    name: str | None = None
    template_id: str | None = None

class SmartMineResponse(BaseModel):
    source_id: str
    status: str  # "queued" | "analyzing" | "generating_config" | "testing" | "mining" | "done" | "error"
    message: str

class SmartMineStatus(BaseModel):
    source_id: str
    status: str
    message: str | None
    progress: dict  # {"pages": int, "records": int, "stage": str}
    created_at: str
    updated_at: str
    cost_estimate: float | None
    success_rate: float | None
```

**Background Task Execution:**

```python
@router.post("/", response_model=SmartMineResponse)
async def create_smart_mine(
    request: SmartMineRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Create source
    source = await crud.create_source(...)
    
    # Queue background task
    background_tasks.add_task(
        _run_smart_mine_background,
        source.id,
        request.url,
        request.template_id,
    )
    
    return SmartMineResponse(
        source_id=source.id,
        status="queued",
        message="Smart mining queued"
    )
```

**Status Endpoint with Polling Support:**

```python
@router.get("/{source_id}/status")
async def get_smart_mine_status(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    source = await crud.get_source(db, source_id)
    
    # Get counts
    pages_count = await crud.count_pages(db, source_id=source_id)
    records_count = await crud.count_records(db, source_id=source_id)
    
    return {
        "source_id": source_id,
        "status": source.status,
        "message": source.error_message,
        "progress": {
            "pages": pages_count,
            "records": records_count,
            "stage": _extract_stage(source.status),
        },
        "created_at": source.created_at.isoformat(),
        "updated_at": source.updated_at.isoformat(),
    }
```

---

### 2. Template Library

**File:** `app/ai/templates.py`

**Requirements:**
- Store templates as JSON files
- Load all templates on startup
- Similarity matching algorithm
- CRUD operations for templates
- Template usage tracking

**Template Schema:**

```python
class Template(TypedDict):
    id: str                    # UUID
    name: str                  # "Art Gallery - Standard"
    description: str           # "Standard template for art galleries..."
    site_type: str            # "art_gallery"
    entity_types: list[str]   # ["artists", "exhibitions"]
    cms: str | None           # "wordpress" | "squarespace" | None
    config: dict              # Full structure_map
    success_rate: float       # 0.0 - 1.0
    usage_count: int          # Track popularity
    created_at: str
    updated_at: str
```

**TemplateLibrary Class:**

```python
class TemplateLibrary:
    def __init__(self, templates_dir: str = "app/ai/template_data"):
        self.templates_dir = Path(templates_dir)
        self.templates: dict[str, Template] = {}
        self._load_templates()
    
    def find_best_match(self, site_analysis: dict) -> Template | None:
        """Find template with highest similarity score."""
        # Scoring algorithm:
        # - Site type match: 40%
        # - Entity types overlap: 30%
        # - CMS match: 20%
        # - Success rate bonus: 10%
        # Minimum threshold: 0.75
    
    def save_template(
        self,
        name: str,
        description: str,
        site_analysis: dict,
        config: dict,
        success_rate: float = 1.0,
    ) -> str:
        """Save new template to library."""
    
    def get_template(self, template_id: str) -> Template | None:
        """Get template by ID."""
    
    def list_templates(
        self,
        site_type: str | None = None,
    ) -> list[Template]:
        """List all templates, optionally filtered."""
    
    def increment_usage(self, template_id: str):
        """Increment usage counter."""
```

**Similarity Scoring:**

```python
def _calculate_similarity(
    self,
    analysis: dict,
    template: Template,
) -> float:
    score = 0.0
    
    # Site type match (40%)
    if analysis.get("site_type") == template["site_type"]:
        score += 0.4
    
    # Entity types overlap (30%)
    analysis_entities = set(analysis.get("entity_types", []))
    template_entities = set(template["entity_types"])
    if analysis_entities:
        overlap = len(analysis_entities & template_entities)
        score += 0.3 * (overlap / len(analysis_entities))
    
    # CMS match (20%)
    if analysis.get("cms") and analysis["cms"] == template.get("cms"):
        score += 0.2
    
    # Success rate bonus (10%)
    score += 0.1 * template.get("success_rate", 0.5)
    
    return score
```

---

### 3. Caching Layer

**File:** `app/ai/cache.py`

**Requirements:**
- Cache site analyses (24 hour TTL)
- Cache generated configs (until site changes)
- Cache template matches (1 hour TTL)
- In-memory cache with expiration
- Optional: Redis backend for production

**Implementation:**

```python
from functools import wraps
import hashlib
import time
from typing import Any, Callable

class SmartMineCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        self._cache: dict[str, dict] = {}
    
    def get(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        entry = self._cache.get(key)
        if not entry:
            return None
        
        if time.time() > entry["expires_at"]:
            del self._cache[key]
            return None
        
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value with TTL in seconds."""
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
        }
    
    def cache_key(self, url: str, operation: str) -> str:
        """Generate cache key."""
        return hashlib.sha256(f"{operation}:{url}".encode()).hexdigest()
    
    def clear(self):
        """Clear all cache."""
        self._cache.clear()

cache = SmartMineCache()

def cached_analysis(func: Callable):
    """Decorator to cache site analysis results."""
    @wraps(func)
    async def wrapper(url: str):
        key = cache.cache_key(url, "analysis")
        cached = cache.get(key)
        if cached:
            logger.info("cache_hit", operation="analysis", url=url)
            return cached
        
        result = await func(url)
        cache.set(key, result, ttl=86400)  # 24 hours
        return result
    return wrapper

# Apply to site_analyzer
from app.ai.site_analyzer import analyze_site_structure
analyze_site_structure = cached_analysis(analyze_site_structure)
```

---

### 4. CRUD Extensions

**File:** `app/db/crud.py`

**Add count methods:**

```python
async def count_pages(
    db: AsyncSession,
    source_id: str,
) -> int:
    """Count total pages for a source."""
    result = await db.execute(
        select(func.count(Page.id)).where(Page.source_id == source_id)
    )
    return result.scalar() or 0

async def count_records(
    db: AsyncSession,
    source_id: str,
) -> int:
    """Count total records for a source."""
    result = await db.execute(
        select(func.count(Record.id)).where(Record.source_id == source_id)
    )
    return result.scalar() or 0
```

---

### 5. Initial Templates

**Script:** `scripts/create_initial_templates.py`

Create 10 initial templates covering common site types:

1. **Art Gallery - Standard** (Squarespace)
2. **Art Gallery - WordPress**
3. **Event Calendar - Eventbrite Style**
4. **Event Calendar - Custom**
5. **Artist Directory - List View**
6. **Artist Directory - Grid View**
7. **Exhibition Site - Museum**
8. **Venue Directory**
9. **Blog - Art News**
10. **E-commerce - Art Sales**

**Template Creation Script:**

```python
from app.ai.templates import template_library
import json

# Template 1: Art Gallery - Standard
art_gallery_config = {
    "crawl_plan": {
        "phases": [
            {
                "phase_name": "root",
                "base_url": "{url}",
                "url_pattern": "/",
                "pagination_type": "none",
                "num_pages": 1
            },
            {
                "phase_name": "artist_directory",
                "base_url": "{url}",
                "url_pattern": "/artists/?",
                "pagination_type": "none",
                "num_pages": 1
            },
            {
                "phase_name": "artist_detail",
                "base_url": "{url}",
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
                "title": "h1.artist-name, h1.entry-title, h1",
                "description": ".artist-bio, .biography, .about-artist, .entry-content p",
                "email": "a[href^='mailto:'], .contact-email, .email",
                "website_url": "a.website, a.external-link[href^='http']:not([href*='{domain}'])",
                "avatar_url": ".profile-photo img, .artist-image img, .featured-image img",
            }
        }
    },
    "page_type_rules": {
        "artist_detail": {
            "page_type_label": "Artist Profile",
            "page_role": "artist_detail",
            "destination_entities": ["artist"],
            "target_record_types": ["artist"],
            "required_fields": ["title"]
        }
    },
    "record_type_rules": {
        "artist": {
            "page_roles": ["artist_detail"],
            "fields": ["title", "description", "email", "website_url", "avatar_url"]
        }
    },
    "follow_rules": {
        "artist_directory": {
            "selectors": ["a[href*='/artists/']"],
            "max_depth": 2
        }
    },
    "asset_rules": {
        "artist_detail": {
            "selectors": [".profile-photo img", ".gallery img", ".artwork img"],
            "roles": {
                ".profile-photo img": "profile",
                ".gallery img": "gallery"
            }
        }
    }
}

template_id = template_library.save_template(
    name="Art Gallery - Standard",
    description="Standard template for art gallery websites with artist profiles. Works with Squarespace, Wix, and custom sites.",
    site_analysis={
        "site_type": "art_gallery",
        "entity_types": ["artists"],
        "cms": None,  # Generic
    },
    config=art_gallery_config,
    success_rate=0.92,
)

print(f"✅ Created template: {template_id}")

# Create 9 more templates...
```

**Note on {url} and {domain} placeholders:**
- Templates use `{url}` placeholder for base_url
- Use `{domain}` in selectors to exclude internal links
- These are replaced when template is applied

---

### 6. Template Application

**Update:** `app/ai/smart_miner.py`

**Replace template stub:**

```python
async def _find_matching_template(
    self,
    site_analysis: dict,
) -> Template | None:
    """Find best matching template."""
    from app.ai.templates import template_library
    
    template = template_library.find_best_match(site_analysis)
    
    if template:
        logger.info(
            "template_matched",
            template_id=template["id"],
            template_name=template["name"],
            similarity_score=self._calculate_similarity(site_analysis, template),
        )
        
        # Increment usage counter
        template_library.increment_usage(template["id"])
    
    return template

async def _load_template(self, template_id: str) -> dict:
    """Load template configuration."""
    from app.ai.templates import template_library
    
    template = template_library.get_template(template_id)
    if not template:
        raise ValueError(f"Template not found: {template_id}")
    
    logger.info("template_loaded", template_id=template_id, template_name=template["name"])
    
    # Increment usage
    template_library.increment_usage(template_id)
    
    return template["config"]
```

**Apply template with URL replacement:**

```python
def _apply_template(self, template_config: dict, url: str) -> dict:
    """Apply template by replacing placeholders."""
    import copy
    import re
    from urllib.parse import urlparse
    
    config = copy.deepcopy(template_config)
    domain = urlparse(url).netloc
    
    # Replace {url} and {domain} placeholders recursively
    config_str = json.dumps(config)
    config_str = config_str.replace("{url}", url)
    config_str = config_str.replace("{domain}", domain)
    
    return json.loads(config_str)
```

---

### 7. API Integration

**Add to:** `app/api/main.py`

```python
from app.api.routes import smart_mining

app.include_router(smart_mining.router)
```

**CORS configuration:**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## TESTING REQUIREMENTS

### API Tests

**test_api_smart_mining.py:**

```python
@pytest.mark.asyncio
async def test_create_smart_mine(client: AsyncClient):
    """Test creating a smart mine request."""
    response = await client.post(
        "/api/smart-mine/",
        json={
            "url": "https://art.co.za",
            "name": "Test Site",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "source_id" in data
    assert data["status"] == "queued"

@pytest.mark.asyncio
async def test_get_status(client: AsyncClient):
    """Test status endpoint."""
    # Create source
    create_resp = await client.post("/api/smart-mine/", json={"url": "https://test.com"})
    source_id = create_resp.json()["source_id"]
    
    # Get status
    status_resp = await client.get(f"/api/smart-mine/{source_id}/status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert "status" in data
    assert "progress" in data

@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient):
    """Test template listing."""
    response = await client.get("/api/smart-mine/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) > 0

@pytest.mark.asyncio
async def test_create_with_template(client: AsyncClient):
    """Test creating smart mine with template."""
    # Get first template
    templates = await client.get("/api/smart-mine/templates")
    template_id = templates.json()[0]["id"]
    
    # Create with template
    response = await client.post(
        "/api/smart-mine/",
        json={
            "url": "https://test.com",
            "template_id": template_id,
        }
    )
    assert response.status_code == 200
```

### Template Tests

**test_ai_templates.py:**

```python
def test_template_library_loads():
    """Test templates load on init."""
    from app.ai.templates import template_library
    assert len(template_library.templates) > 0

def test_find_best_match():
    """Test similarity matching."""
    from app.ai.templates import template_library
    
    analysis = {
        "site_type": "art_gallery",
        "entity_types": ["artists"],
        "cms": "wordpress",
    }
    
    match = template_library.find_best_match(analysis)
    assert match is not None
    assert match["site_type"] == "art_gallery"

def test_similarity_scoring():
    """Test similarity score calculation."""
    from app.ai.templates import TemplateLibrary
    
    lib = TemplateLibrary()
    
    # Perfect match
    score = lib._calculate_similarity(
        {"site_type": "art_gallery", "entity_types": ["artists"], "cms": "wordpress"},
        {
            "site_type": "art_gallery",
            "entity_types": ["artists"],
            "cms": "wordpress",
            "success_rate": 0.9,
        }
    )
    assert score >= 0.9  # Near perfect

def test_save_and_get_template():
    """Test saving and retrieving templates."""
    from app.ai.templates import template_library
    
    template_id = template_library.save_template(
        name="Test Template",
        description="Test",
        site_analysis={"site_type": "test", "entity_types": []},
        config={"test": True},
    )
    
    retrieved = template_library.get_template(template_id)
    assert retrieved["name"] == "Test Template"
```

### Cache Tests

**test_ai_cache.py:**

```python
def test_cache_set_get():
    """Test basic cache operations."""
    from app.ai.cache import SmartMineCache
    
    cache = SmartMineCache()
    cache.set("test_key", {"data": "value"}, ttl=60)
    
    result = cache.get("test_key")
    assert result == {"data": "value"}

def test_cache_expiration():
    """Test cache TTL expiration."""
    import time
    from app.ai.cache import SmartMineCache
    
    cache = SmartMineCache()
    cache.set("test_key", "value", ttl=1)
    
    # Should exist
    assert cache.get("test_key") == "value"
    
    # Wait for expiration
    time.sleep(2)
    
    # Should be None
    assert cache.get("test_key") is None

@pytest.mark.asyncio
async def test_cached_analysis():
    """Test analysis caching decorator."""
    from app.ai.site_analyzer import analyze_site_structure
    from app.ai.cache import cache
    
    # Clear cache
    cache.clear()
    
    # First call - cache miss
    result1 = await analyze_site_structure("https://test.com")
    
    # Second call - cache hit (should be instant)
    result2 = await analyze_site_structure("https://test.com")
    
    assert result1 == result2
```

---

## PERFORMANCE TARGETS

- API response time (create): < 200ms
- API response time (status): < 100ms
- Template matching: < 50ms
- Cache hit ratio: > 60% after 1 week
- Template hit ratio: > 40% initially, > 70% after 3 months

---

## MONITORING & LOGGING

**Track these metrics:**

```python
# API metrics
logger.info(
    "api_smart_mine_created",
    source_id=source_id,
    url=url,
    template_id=template_id,
    response_time_ms=response_time,
)

# Template metrics
logger.info(
    "template_matched",
    template_id=template_id,
    similarity_score=score,
    url=url,
)

# Cache metrics
logger.info(
    "cache_hit",
    operation=operation,
    url=url,
)

logger.info(
    "cache_miss",
    operation=operation,
    url=url,
)
```

---

## DOCUMENTATION

Create `docs/smart_mode_week2_api.md`:

```markdown
# Smart Mode API Documentation

## Endpoints

### POST /api/smart-mine/
Start smart mining for a URL.

**Request:**
```json
{
  "url": "https://art.co.za",
  "name": "Art.co.za",
  "template_id": "uuid-optional"
}
```

**Response:**
```json
{
  "source_id": "uuid",
  "status": "queued",
  "message": "Smart mining queued"
}
```

### GET /api/smart-mine/{id}/status
Get real-time mining status.

**Response:**
```json
{
  "source_id": "uuid",
  "status": "mining",
  "message": null,
  "progress": {
    "pages": 47,
    "records": 12,
    "stage": "mining"
  },
  "created_at": "2026-04-23T...",
  "updated_at": "2026-04-23T..."
}
```

### GET /api/smart-mine/templates
List available templates.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Art Gallery - Standard",
    "description": "...",
    "site_type": "art_gallery",
    "entity_types": ["artists"],
    "usage_count": 42,
    "success_rate": 0.92
  }
]
```

## Status Values

- `queued` - Waiting to start
- `analyzing` - Analyzing site structure
- `generating_config` - Generating configuration
- `testing` - Testing configuration
- `refining` - Refining configuration
- `mining` - Crawling and extracting
- `done` - Complete
- `error` - Failed
- `needs_review` - Needs manual configuration

## Template System

Templates are pre-built configurations for common site types.
When a new URL is submitted, the system:
1. Analyzes the site structure
2. Finds best matching template (if similarity > 0.75)
3. Applies template with URL substitution
4. Tests and refines if needed

Template matching is based on:
- Site type (40% weight)
- Entity types overlap (30% weight)
- CMS match (20% weight)
- Template success rate (10% weight)
```

---

## WEEK 2 COMPLETION CRITERIA

**Must have:**
- [ ] All 5 API endpoints working
- [ ] Background job processing functional
- [ ] Template library with 10 initial templates
- [ ] Caching layer reducing redundant API calls
- [ ] Template matching algorithm tested
- [ ] All tests passing (>90% coverage)
- [ ] API documentation complete
- [ ] Frontend-ready endpoints

**Success metrics:**
- API response time < 200ms: ✅
- Template matching in < 50ms: ✅
- 10 templates created: ✅
- Template hit rate > 30% in testing: ✅
- Cache hit rate > 50% in testing: ✅
- All integration tests passing: ✅

---

## HANDOFF NOTES FOR WEEK 3

After Week 2 completion, provide:
1. API endpoint performance metrics
2. Template hit rates observed
3. Cache effectiveness (hit/miss ratio)
4. Any API design changes
5. Recommendations for frontend integration
6. Known issues with background jobs

---

# CODEX EXECUTION PROMPT

I am continuing Week 2 of the Smart Mode implementation for Artio Mine Bot.

**Week 1 Status:** ✅ Complete
- OpenAI integration working
- Site analyzer, config generator, smart miner orchestrator implemented
- Quality assurance and testing working
- Core AI services functional

**Week 2 Goal:** Expose Smart Mode via API, add background processing, implement template library

## Your Task

Implement the API layer and template system:

1. **Smart Mining API Routes** (`app/api/routes/smart_mining.py`)
   - POST /api/smart-mine/ - Create smart mine request
   - GET /api/smart-mine/{id}/status - Get real-time status
   - POST /api/smart-mine/{id}/retry - Retry failed mine
   - GET /api/smart-mine/templates - List templates
   - GET /api/smart-mine/templates/{id} - Get template details
   - Use FastAPI BackgroundTasks for async execution
   - Add proper error handling and validation

2. **Template Library** (`app/ai/templates.py`)
   - TemplateLibrary class with JSON file storage
   - Template similarity matching algorithm
   - CRUD operations for templates
   - Usage tracking
   - Template application with URL/domain substitution

3. **Initial Templates** (`scripts/create_initial_templates.py`)
   - Create 10 templates covering common site types
   - Art galleries (Squarespace, WordPress)
   - Event calendars
   - Artist directories
   - Save to app/ai/template_data/

4. **Caching Layer** (`app/ai/cache.py`)
   - Simple in-memory cache with TTL
   - Decorator for caching site analysis
   - Cache key generation
   - Expiration handling

5. **CRUD Extensions** (`app/db/crud.py`)
   - Add count_pages() method
   - Add count_records() method
   - Use for status endpoint

6. **Update Smart Miner** (`app/ai/smart_miner.py`)
   - Replace template stubs with real template loading
   - Implement template matching
   - Add template application logic
   - Increment usage counters

7. **Integration** (`app/api/main.py`)
   - Include smart_mining router
   - Configure CORS for frontend
   - Add error handlers

8. **Comprehensive Tests**
   - API endpoint tests
   - Template library tests
   - Cache tests
   - Integration tests

## Technical Requirements

- Use FastAPI BackgroundTasks for job execution
- Templates stored as JSON files in app/ai/template_data/
- Template matching uses weighted similarity score
- Minimum match threshold: 0.75
- Cache TTL: 24 hours for analysis, 1 hour for template matches
- All API responses use Pydantic models
- Proper HTTP status codes (200, 404, 422, 500)
- Structured logging for all operations

## Template Format

Templates use placeholders:
- `{url}` - Replaced with actual site URL
- `{domain}` - Replaced with domain name (for excluding internal links)

Example:
```json
{
  "crawl_plan": {
    "phases": [{
      "base_url": "{url}",
      "url_pattern": "/artists/[a-z0-9\\-]+/?"
    }]
  }
}
```

## Success Criteria

After implementation:
1. Can POST to /api/smart-mine/ and get source_id back
2. Can GET status and see real-time progress
3. Template library has 10 templates
4. Template matching finds appropriate templates
5. Cache reduces redundant AI calls
6. Background jobs execute without blocking API
7. All tests pass with >90% coverage

## Files to Create/Modify

**New files:**
- app/api/routes/smart_mining.py
- app/ai/templates.py
- app/ai/cache.py
- app/ai/template_data/*.json (10 files)
- scripts/create_initial_templates.py
- tests/test_api_smart_mining.py
- tests/test_ai_templates.py
- tests/test_ai_cache.py
- docs/smart_mode_week2_api.md

**Modify:**
- app/api/main.py (add router)
- app/db/crud.py (add count methods)
- app/ai/smart_miner.py (add template integration)

Start implementation now. Create the complete API layer with template system.

When complete, provide:
1. Summary of implemented features
2. Template hit rate in initial testing
3. Cache effectiveness metrics
4. API performance measurements
5. Known limitations
6. Recommendations for Week 3 (frontend integration)
