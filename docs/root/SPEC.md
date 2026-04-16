# SPEC.md — Artio Miner: Product Specification

## 1. Purpose

Artio Miner is a standalone portable web mining application. The operator points it at any
art-related website URL. The system automatically:

1. Maps the site structure — navigation, sections, categories
2. Classifies each section by content type (events, exhibitions, artists, venues, artworks)
3. Crawls each section to a configurable depth
4. Extracts structured data from each page using AI
5. Collects all image URLs found on extracted pages
6. Scores each extracted record by confidence
7. Presents records in an admin UI for review, editing, and approval
8. Exports approved records to the Artio platform API

The system must work on any website regardless of CMS or structure. It must handle
JavaScript-rendered sites (using Playwright). It must be runnable locally with a single
command and require only an OpenAI API key to operate.

---

## 2. Directory Structure

```
artio-miner/
├── AGENTS.md
├── SPEC.md
├── SCHEMA.md
├── API.md
├── UI.md
├── STACK.md
├── README.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.frontend
├── scripts/
│   └── start.sh
├── data/
│   └── .gitkeep          ← SQLite DB goes here (gitignored)
├── app/
│   ├── __init__.py
│   ├── config.py          ← settings from env vars
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py    ← engine, session factory, init_db
│   │   ├── models.py      ← SQLAlchemy ORM models
│   │   ├── crud.py        ← all database operations
│   │   └── migrations/    ← Alembic migrations
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── fetcher.py     ← HTTP + Playwright fetcher
│   │   ├── site_mapper.py ← maps site structure from homepage
│   │   ├── link_follower.py ← crawl queue and link extraction
│   │   └── robots.py      ← robots.txt parsing
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── client.py      ← OpenAI client with retry
│   │   ├── classifier.py  ← page type classification
│   │   ├── confidence.py  ← confidence scoring
│   │   └── extractors/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── event.py
│   │       ├── exhibition.py
│   │       ├── artist.py
│   │       ├── venue.py
│   │       └── artwork.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── runner.py      ← orchestrates the full pipeline
│   │   ├── queue.py       ← job queue backed by SQLite
│   │   └── image_collector.py ← image URL extraction + validation
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py        ← FastAPI app entry point
│   │   ├── deps.py        ← shared dependencies (db session etc)
│   │   ├── schemas.py     ← Pydantic request/response models
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── sources.py
│   │       ├── mine.py
│   │       ├── pages.py
│   │       ├── records.py
│   │       ├── images.py
│   │       ├── export.py
│   │       └── stats.py
│   └── export/
│       ├── __init__.py
│       ├── artio_client.py
│       └── formatter.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── lib/
│       │   ├── api.ts     ← typed API client
│       │   └── utils.ts
│       ├── components/
│       │   ├── ui/        ← shadcn components
│       │   └── shared/    ← app-specific shared components
│       └── pages/
│           ├── Dashboard.tsx
│           ├── Sources.tsx
│           ├── SourceDetail.tsx
│           ├── Pages.tsx
│           ├── Records.tsx
│           ├── RecordDetail.tsx
│           ├── Images.tsx
│           └── Export.tsx
└── tests/
    ├── conftest.py
    ├── test_db.py
    ├── test_crawler.py
    ├── test_ai.py
    ├── test_pipeline.py
    └── test_api.py
```

---

## 3. Core Pipeline

### Step 1 — Site Mapping

Input: a URL string (e.g. `https://art.co.za`)

Process:
1. Fetch homepage HTML (try httpx first, Playwright fallback for JS sites)
2. Parse all `<a>` tags in `<nav>`, `<header>`, `<footer>` elements
3. Filter to same-domain internal links only
4. For each unique path, fetch the page and detect its content type
5. Group paths into sections: artists, events, exhibitions, venues, what's-on, other
6. Detect pagination pattern per section (letter A-Z, page numbers, infinite scroll)
7. Return a `SiteMap` object with sections and their base URLs

Output: `SiteMap` stored in the `Source` record as JSON

### Step 2 — Section Classification

For each section URL, classify using this priority:
1. JSON-LD `@type` field — if present, use it directly
2. URL pattern matching — `/events/`, `/exhibitions/`, `/artists/`, `/what.*on/`
3. AI classification — send cleaned HTML snippet to GPT-4o with strict schema

Content types:
- `artist_directory` — list of artist profiles
- `artist_profile` — single artist page
- `event_listing` — list of upcoming/past events
- `event_detail` — single event page
- `exhibition_listing` — list of exhibitions
- `exhibition_detail` — single exhibition page
- `venue_profile` — gallery or venue page
- `artwork_listing` — artwork grid or shop
- `artwork_detail` — single artwork page
- `category` — general category listing page
- `unknown` — cannot determine

### Step 3 — Crawling

For each enabled section in the SiteMap:
1. Build a crawl queue starting from the section base URL
2. Fetch each URL (respect `CRAWL_DELAY_MS` between requests)
3. Check robots.txt before crawling any URL
4. Extract all same-domain links from the page
5. For each link: classify the linked page and add to queue if relevant
6. Stop when: max depth reached, max pages reached, or no new URLs found
7. Store every crawled page in the `Page` table with its HTML (truncated to 500KB)

### Step 4 — Extraction

For each crawled page, based on its `page_type`:
- `artist_profile` → run `ArtistExtractor`
- `event_detail` → run `EventExtractor`
- `exhibition_detail` → run `ExhibitionExtractor`
- `venue_profile` → run `VenueExtractor`
- `artwork_detail` → run `ArtworkExtractor`
- listing pages → extract child links only, add to queue

Each extractor:
1. Preprocesses HTML — strips nav, footer, scripts, styles, ads
2. Extracts all image URLs from the page (filtered for relevance)
3. Sends cleaned HTML to GPT-4o with a strict JSON schema
4. Validates the response against the schema
5. Scores confidence based on completeness and signal quality
6. Stores result as a `Record`

### Step 5 — Image Collection

For every extracted record:
1. Collect all image URLs from the page
2. Validate each URL is accessible (HEAD request, check Content-Type)
3. Filter out: SVGs, icons < 100×100px, tracking pixels, logos
4. Classify each image: `profile`, `artwork`, `poster`, `venue`, `unknown`
5. Store as `Image` records linked to the `Record`

### Step 6 — Confidence Scoring

Score each record 0–100 based on:

| Signal | Points |
|--------|--------|
| Title or name present | +20 |
| Description or bio present | +15 |
| At least one date (for events) | +15 |
| Venue name present | +10 |
| At least one artist linked | +10 |
| At least one valid image URL | +15 |
| JSON-LD source (high reliability) | +10 |
| AI extracted with high model confidence | +5 |

Bands:
- HIGH: 70–100
- MEDIUM: 40–69
- LOW: 0–39

### Step 7 — Admin Review

Admin views records grouped by source and type. Can:
- Browse all records with filters (type, confidence, status)
- View individual record with all extracted fields and images
- Edit any field inline
- Approve or reject individual records
- Bulk approve all HIGH confidence records
- Select primary image for each record
- Export approved records to Artio

### Step 8 — Export

Approved records are formatted and sent to the Artio API:
- `POST {ARTIO_API_URL}/api/feed/ingest`
- Payload: array of formatted records with image URLs
- Auth: `Authorization: Bearer {ARTIO_API_KEY}`
- On success: mark records as `exported`, set `exported_at`

---

## 4. Content Types and Extracted Fields

### Event
```json
{
  "title": "string",
  "description": "string | null",
  "start_date": "ISO date string | null",
  "end_date": "ISO date string | null",
  "venue_name": "string | null",
  "venue_address": "string | null",
  "artist_names": ["string"],
  "ticket_url": "string | null",
  "is_free": "boolean | null",
  "price_text": "string | null",
  "image_urls": ["string"]
}
```

### Exhibition
```json
{
  "title": "string",
  "description": "string | null",
  "start_date": "ISO date string | null",
  "end_date": "ISO date string | null",
  "venue_name": "string | null",
  "artist_names": ["string"],
  "curator": "string | null",
  "image_urls": ["string"]
}
```

### Artist
```json
{
  "name": "string",
  "bio": "string | null",
  "nationality": "string | null",
  "birth_year": "integer | null",
  "mediums": ["string"],
  "website_url": "string | null",
  "instagram_url": "string | null",
  "email": "string | null",
  "collections": ["string"],
  "avatar_url": "string | null",
  "image_urls": ["string"]
}
```

### Venue
```json
{
  "name": "string",
  "description": "string | null",
  "address": "string | null",
  "city": "string | null",
  "country": "string | null",
  "website_url": "string | null",
  "phone": "string | null",
  "email": "string | null",
  "opening_hours": "string | null",
  "image_urls": ["string"]
}
```

### Artwork
```json
{
  "title": "string",
  "artist_name": "string | null",
  "medium": "string | null",
  "year": "integer | null",
  "dimensions": "string | null",
  "description": "string | null",
  "price": "string | null",
  "image_urls": ["string"]
}
```

---

## 5. Error Handling

- Failed fetch: store `Page` with `status=error`, `error_message`, continue crawling
- Failed AI extraction: store `Record` with `status=error`, `raw_error`, allow retry
- Failed image validation: skip image, log warning
- Robots.txt blocked: skip URL, log info
- Rate limit from OpenAI: exponential backoff, max 3 retries, then mark job failed
- Connection timeout: retry once after 5 seconds, then mark page as error
- JS-required page (httpx returns empty body): automatically retry with Playwright

---

## 6. Performance Constraints

- Respect `CRAWL_DELAY_MS` between all HTTP requests to the same domain
- Maximum `MAX_PAGES_PER_SOURCE` pages per crawl run
- Maximum `MAX_CRAWL_DEPTH` link depth from root URL
- Playwright sessions: open one at a time, close after each use
- OpenAI calls: maximum 10 concurrent requests
- HTML stored in DB: truncate to 500KB before storing
- Image validation: HEAD requests only (never download full images)
