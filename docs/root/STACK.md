# STACK.md — Artio Miner: Technology Stack

## Python Backend

### Runtime
- Python 3.11+
- FastAPI 0.115+
- Uvicorn (ASGI server)

### Database
- SQLAlchemy 2.0+ (async ORM)
- aiosqlite (async SQLite driver)
- Alembic (migrations)

### HTTP / Crawling
- httpx (async HTTP client — primary fetcher)
- playwright (async browser automation — JS-rendered sites fallback)
- beautifulsoup4 (HTML parsing)
- lxml (HTML parser backend for bs4)

### AI
- openai (official Python SDK, v1.0+)
- tiktoken (token counting for HTML truncation)

### Utilities
- pydantic v2 (data validation, settings)
- python-dotenv (env file loading)
- structlog (structured logging)
- tenacity (retry logic with exponential backoff)

### Testing
- pytest
- pytest-asyncio
- httpx (AsyncClient for API tests)
- pytest-mock
- respx (mock httpx requests)

---

## pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "artio-miner"
version = "1.0.0"
description = "Artio web mining and data extraction tool"
requires-python = ">=3.11"

dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "sqlalchemy>=2.0.0",
  "aiosqlite>=0.20.0",
  "alembic>=1.13.0",
  "httpx>=0.27.0",
  "playwright>=1.44.0",
  "beautifulsoup4>=4.12.0",
  "lxml>=5.2.0",
  "openai>=1.30.0",
  "tiktoken>=0.7.0",
  "pydantic>=2.7.0",
  "pydantic-settings>=2.3.0",
  "python-dotenv>=1.0.0",
  "structlog>=24.1.0",
  "tenacity>=8.3.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "pytest-asyncio>=0.23.0",
  "pytest-mock>=3.14.0",
  "respx>=0.21.0",
  "ruff>=0.4.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
```

---

## React Frontend

### Runtime
- Node.js 20+
- React 18
- TypeScript 5+ (strict mode)

### Build
- Vite 5+

### UI
- tailwindcss 3+
- shadcn/ui (component library — install components individually)
- lucide-react (icons)
- class-variance-authority
- clsx
- tailwind-merge

### State & Data
- @tanstack/react-query v5
- react-router-dom v6
- axios

### package.json

```json
{
  "name": "artio-miner-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "@tanstack/react-query": "^5.40.0",
    "axios": "^1.7.0",
    "lucide-react": "^0.383.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.3.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@typescript-eslint/eslint-plugin": "^7.0.0",
    "@typescript-eslint/parser": "^7.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.57.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.4.0",
    "vite": "^5.3.0"
  }
}
```

---

## Docker

### Dockerfile (Python backend)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install -e ".[dev]"

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Dockerfile.frontend

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### docker-compose.yml

```yaml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - .:/app
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/miner.db

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "5173:80"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - api
```

---

## Configuration (`app/config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"
    database_url: str = "sqlite+aiosqlite:///./data/miner.db"
    artio_api_url: str | None = None
    artio_api_key: str | None = None
    max_crawl_depth: int = 3
    max_pages_per_source: int = 500
    crawl_delay_ms: int = 1000
    playwright_enabled: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## AI System Prompts

### Page Classifier System Prompt

```
You classify web pages from art websites into one of these types:
- artist_profile: A page dedicated to one specific artist with bio and/or portfolio
- event_detail: A single event or show with title, dates, and venue
- exhibition_detail: A single exhibition with title, dates, and description
- venue_profile: A gallery or museum page with description and contact info
- artwork_detail: A single artwork listing with title, medium, and image
- artist_directory: An index listing multiple artists (A-Z or paginated)
- event_listing: An index listing multiple upcoming or past events
- exhibition_listing: An index listing multiple exhibitions
- artwork_listing: A grid of artworks for sale or display
- category: A general category or navigation page
- unknown: Cannot determine from the content provided

Return JSON only:
{
  "page_type": "<type>",
  "confidence": <0-100>,
  "reasoning": "<one sentence>"
}

Rules:
- Return exactly one type
- Base decision only on the HTML content provided
- Confidence 80+ = certain, 50-79 = probable, below 50 = uncertain
- If page is a 404, login wall, or broken return unknown with confidence 0
```

### Event Extractor System Prompt

```
Extract structured data from this art event or exhibition page.
Return ONLY valid JSON matching this exact schema. Use null for missing fields.
Do not invent information not present on the page.

Schema:
{
  "title": "string — event title",
  "description": "string | null — event description",
  "start_date": "string | null — ISO date e.g. 2026-04-15",
  "end_date": "string | null — ISO date",
  "venue_name": "string | null",
  "venue_address": "string | null",
  "artist_names": ["string"] — array of artist names,
  "ticket_url": "string | null — full URL",
  "is_free": "boolean | null",
  "price_text": "string | null — raw price string",
  "image_urls": ["string"] — full URLs of relevant images
}
```

### Artist Extractor System Prompt

```
Extract structured data from this artist profile page.
Return ONLY valid JSON. Use null for missing fields. Do not invent.

Schema:
{
  "name": "string — artist full name",
  "bio": "string | null — biographical text",
  "nationality": "string | null",
  "birth_year": "integer | null",
  "mediums": ["string"] — artistic mediums exactly as stated,
  "website_url": "string | null — full URL",
  "instagram_url": "string | null — full URL",
  "email": "string | null",
  "collections": ["string"] — named institutions holding their work,
  "avatar_url": "string | null — URL of artist portrait photo NOT artwork",
  "image_urls": ["string"] — other relevant image URLs
}
```

### Exhibition Extractor System Prompt

```
Extract structured data from this art exhibition page.
Return ONLY valid JSON. Use null for missing fields. Do not invent.

Schema:
{
  "title": "string — exhibition title",
  "description": "string | null",
  "start_date": "string | null — ISO date",
  "end_date": "string | null — ISO date",
  "venue_name": "string | null",
  "artist_names": ["string"],
  "curator": "string | null",
  "image_urls": ["string"] — full URLs of exhibition images
}
```

### Venue Extractor System Prompt

```
Extract structured data from this art gallery or venue page.
Return ONLY valid JSON. Use null for missing fields. Do not invent.

Schema:
{
  "name": "string — venue or gallery name",
  "description": "string | null",
  "address": "string | null",
  "city": "string | null",
  "country": "string | null",
  "website_url": "string | null",
  "phone": "string | null",
  "email": "string | null",
  "opening_hours": "string | null",
  "image_urls": ["string"] — venue exterior/interior images only
}
```

### Artwork Extractor System Prompt

```
Extract structured data from this artwork page.
Return ONLY valid JSON. Use null for missing fields. Do not invent.

Schema:
{
  "title": "string — artwork title",
  "artist_name": "string | null",
  "medium": "string | null — e.g. Oil on canvas",
  "year": "integer | null",
  "dimensions": "string | null — e.g. 90 x 120 cm",
  "description": "string | null",
  "price": "string | null — raw price string",
  "image_urls": ["string"] — high-resolution artwork images only, not thumbnails
}
```

### Site Mapper System Prompt

```
Analyse this art website homepage and identify all content sections.
Return ONLY valid JSON.

Schema:
{
  "platform": "string — wordpress | squarespace | custom | unknown",
  "sections": [
    {
      "name": "string — human readable name e.g. Artists A-Z",
      "url": "string — full section base URL",
      "content_type": "artist_directory | event_listing | exhibition_listing | artwork_listing | venue_profile | unknown",
      "pagination_type": "letter | numbered | none",
      "index_pattern": "string | null — URL with [letter] or [page] placeholder",
      "confidence": 0-100
    }
  ]
}

Rules:
- Only include sections you can see navigation links for
- Do not invent sections not linked from the page
- For letter-paginated directories use [letter] placeholder
- For numbered pages use [page] placeholder
```
