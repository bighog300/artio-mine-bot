# SCHEMA.md — Artio Miner: Database Schema

## Database

SQLite via SQLAlchemy (async with aiosqlite). All models use string UUIDs as primary keys
generated with `uuid.uuid4()`. All timestamps are UTC.

## Models

### Source

Represents a website being mined.

```python
class Source(Base):
    __tablename__ = "sources"

    id: str                  # UUID primary key
    url: str                 # The root URL provided by the operator (unique)
    name: str | None         # Optional display name
    status: str              # pending | mapping | crawling | extracting | done | error | paused
    site_map: str | None     # JSON — SiteMap object from site mapper
    total_pages: int         # Count of crawled pages
    total_records: int       # Count of extracted records
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    last_crawled_at: datetime | None

    # Relationships
    pages: list[Page]
    records: list[Record]
    jobs: list[Job]
```

### Page

Represents a single crawled URL.

```python
class Page(Base):
    __tablename__ = "pages"

    id: str                  # UUID primary key
    source_id: str           # FK → Source
    url: str                 # Final URL after redirects
    original_url: str        # URL as found in link
    page_type: str           # unknown | artist_profile | event_detail | exhibition_detail |
                             # venue_profile | artwork_detail | artist_directory |
                             # event_listing | exhibition_listing | artwork_listing | category
    status: str              # pending | fetched | classified | extracted | error | skipped
    depth: int               # How many links deep from root (0 = root)
    fetch_method: str | None # httpx | playwright
    html_truncated: bool     # True if HTML was truncated before storing
    html: str | None         # Cleaned HTML (max 500KB)
    title: str | None        # <title> tag content
    error_message: str | None
    crawled_at: datetime | None
    extracted_at: datetime | None
    created_at: datetime

    # Relationships
    source: Source
    records: list[Record]
    images: list[Image]

    __table_args__ = (UniqueConstraint("source_id", "url"),)
```

### Record

Represents an extracted piece of art-world content.

```python
class Record(Base):
    __tablename__ = "records"

    id: str                  # UUID primary key
    source_id: str           # FK → Source
    page_id: str | None      # FK → Page (nullable for manually created)
    record_type: str         # event | exhibition | artist | venue | artwork
    status: str              # pending | approved | rejected | exported | error

    # Core fields (shared)
    title: str | None        # Event title, artist name, venue name, artwork title
    description: str | None
    source_url: str | None   # Original page URL

    # Event / Exhibition fields
    start_date: str | None   # ISO date string
    end_date: str | None     # ISO date string
    venue_name: str | None
    venue_address: str | None
    artist_names: str        # JSON array of strings — default "[]"
    ticket_url: str | None
    is_free: bool | None
    price_text: str | None
    curator: str | None

    # Artist fields
    bio: str | None
    nationality: str | None
    birth_year: int | None
    mediums: str             # JSON array — default "[]"
    collections: str         # JSON array — default "[]"
    website_url: str | None
    instagram_url: str | None
    email: str | None
    avatar_url: str | None

    # Venue fields
    address: str | None
    city: str | None
    country: str | None
    phone: str | None
    opening_hours: str | None

    # Artwork fields
    medium: str | None
    year: int | None
    dimensions: str | None
    price: str | None

    # Extraction metadata
    raw_data: str | None     # Full JSON blob from AI extractor
    raw_error: str | None    # Error from failed extraction
    extraction_model: str | None  # e.g. "gpt-4o"
    extraction_provider: str | None  # "openai"

    # Confidence
    confidence_score: int    # 0–100
    confidence_band: str     # LOW | MEDIUM | HIGH
    confidence_reasons: str  # JSON array of reason strings

    # Admin fields
    admin_notes: str | None
    primary_image_id: str | None  # FK → Image (selected by admin)
    exported_at: datetime | None

    created_at: datetime
    updated_at: datetime

    # Relationships
    source: Source
    page: Page | None
    images: list[Image]
    primary_image: Image | None
```

### Image

Represents an image URL found on a crawled page, linked to a record.

```python
class Image(Base):
    __tablename__ = "images"

    id: str                  # UUID primary key
    record_id: str | None    # FK → Record
    page_id: str | None      # FK → Page
    source_id: str           # FK → Source
    url: str                 # Full image URL
    alt_text: str | None     # img alt attribute
    image_type: str          # profile | artwork | poster | venue | unknown
    width: int | None        # From img attributes or HEAD response
    height: int | None
    mime_type: str | None    # From Content-Type header
    is_valid: bool           # True if HEAD request succeeded
    confidence: int          # 0–100 classification confidence
    created_at: datetime

    # Relationships
    record: Record | None
    page: Page | None

    __table_args__ = (UniqueConstraint("record_id", "url"),)
```

### Job

Represents a crawl or extraction job in the queue.

```python
class Job(Base):
    __tablename__ = "jobs"

    id: str                  # UUID primary key
    source_id: str           # FK → Source
    job_type: str            # map_site | crawl_section | extract_page | validate_images | export
    status: str              # pending | running | done | failed | cancelled
    payload: str | None      # JSON — job-specific parameters
    result: str | None       # JSON — job result summary
    error_message: str | None
    attempts: int            # Retry count
    max_attempts: int        # Default 3
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    # Relationships
    source: Source
```

## Indexes

```python
# Page indexes
Index("ix_pages_source_id", Page.source_id)
Index("ix_pages_status", Page.status)
Index("ix_pages_page_type", Page.page_type)

# Record indexes
Index("ix_records_source_id", Record.source_id)
Index("ix_records_status", Record.status)
Index("ix_records_record_type", Record.record_type)
Index("ix_records_confidence_band", Record.confidence_band)

# Image indexes
Index("ix_images_record_id", Image.record_id)
Index("ix_images_source_id", Image.source_id)

# Job indexes
Index("ix_jobs_source_id", Job.source_id)
Index("ix_jobs_status", Job.status)
```

## CRUD Operations Required

All functions in `app/db/crud.py` must be async.

### Source CRUD
```python
async def create_source(db, url: str, name: str | None) -> Source
async def get_source(db, source_id: str) -> Source | None
async def get_source_by_url(db, url: str) -> Source | None
async def list_sources(db, skip: int, limit: int) -> list[Source]
async def update_source(db, source_id: str, **kwargs) -> Source
async def delete_source(db, source_id: str) -> bool
async def get_source_stats(db, source_id: str) -> dict
```

### Page CRUD
```python
async def create_page(db, source_id: str, url: str, **kwargs) -> Page
async def get_page(db, page_id: str) -> Page | None
async def get_or_create_page(db, source_id: str, url: str) -> tuple[Page, bool]
async def list_pages(db, source_id: str, status: str | None, page_type: str | None,
                     skip: int, limit: int) -> list[Page]
async def update_page(db, page_id: str, **kwargs) -> Page
async def count_pages(db, source_id: str, status: str | None) -> int
```

### Record CRUD
```python
async def create_record(db, source_id: str, record_type: str, **kwargs) -> Record
async def get_record(db, record_id: str) -> Record | None
async def list_records(db, source_id: str | None, record_type: str | None,
                        status: str | None, confidence_band: str | None,
                        skip: int, limit: int) -> list[Record]
async def update_record(db, record_id: str, **kwargs) -> Record
async def approve_record(db, record_id: str) -> Record
async def reject_record(db, record_id: str) -> Record
async def bulk_approve(db, source_id: str, min_confidence: int) -> int
async def count_records(db, source_id: str | None, status: str | None) -> int
```

### Image CRUD
```python
async def create_image(db, source_id: str, url: str, **kwargs) -> Image
async def list_images(db, record_id: str | None, source_id: str | None,
                       image_type: str | None, skip: int, limit: int) -> list[Image]
async def set_primary_image(db, record_id: str, image_id: str) -> Record
```

### Job CRUD
```python
async def create_job(db, source_id: str, job_type: str, payload: dict) -> Job
async def get_next_pending_job(db) -> Job | None
async def update_job_status(db, job_id: str, status: str, **kwargs) -> Job
async def list_jobs(db, source_id: str | None, status: str | None) -> list[Job]
```
