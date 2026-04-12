# AGENTS.md — Artio Miner: Codex Build Instructions

## Overview

You are building **Artio Miner** — a standalone Python web scraping and data mining application.
Its purpose is to allow an operator to point it at any art-related website (e.g. art.co.za),
automatically map the site structure, extract all art-related content (events, exhibitions,
artists, venues, artworks), score confidence, and manage the data through an admin UI until
records are ready for export to the Artio platform.

Read ALL documents in this repository before writing any code:
1. `AGENTS.md` (this file) — build instructions and rules
2. `SPEC.md` — full product specification
3. `SCHEMA.md` — database schema definitions
4. `API.md` — all API endpoint specifications
5. `UI.md` — admin UI page specifications
6. `STACK.md` — technology stack and dependencies

---

## Build Order

Follow this EXACT order. Do not skip phases. Commit after each phase.

### Phase 0 — Project scaffold
- Create directory structure exactly as specified in `SPEC.md § Directory Structure`
- Create `pyproject.toml` with all dependencies from `STACK.md`
- Create `README.md` with setup instructions
- Create `.env.example` with all required environment variables
- Create `.gitignore`
- Commit: `feat: scaffold project structure`

### Phase 1 — Database layer
- Create `app/db/models.py` — SQLAlchemy models from `SCHEMA.md`
- Create `app/db/database.py` — engine, session, init
- Create `app/db/migrations/` — Alembic setup
- Run `alembic init` and configure for SQLite
- Create initial migration
- Write `app/db/crud.py` — all CRUD operations
- Test: `python -m pytest tests/test_db.py`
- Commit: `feat: database models and CRUD`

### Phase 2 — Crawler engine
- Create `app/crawler/fetcher.py` — HTTP fetcher with Playwright fallback
- Create `app/crawler/site_mapper.py` — homepage → nav links → section groups
- Create `app/crawler/link_follower.py` — crawl queue, depth control, dedup
- Create `app/crawler/robots.py` — robots.txt respect
- Test: `python -m pytest tests/test_crawler.py`
- Commit: `feat: crawler engine`

### Phase 3 — AI classifier and extractors
- Create `app/ai/client.py` — OpenAI client wrapper with retry
- Create `app/ai/classifier.py` — page type classification
- Create `app/ai/extractors/base.py` — base extractor class
- Create `app/ai/extractors/event.py` — event extractor
- Create `app/ai/extractors/exhibition.py` — exhibition extractor
- Create `app/ai/extractors/artist.py` — artist extractor
- Create `app/ai/extractors/venue.py` — venue extractor
- Create `app/ai/extractors/artwork.py` — artwork extractor
- Create `app/ai/confidence.py` — confidence scoring
- Test: `python -m pytest tests/test_ai.py`
- Commit: `feat: AI classifier and extractors`

### Phase 4 — Pipeline orchestrator
- Create `app/pipeline/runner.py` — orchestrates crawl → classify → extract → score
- Create `app/pipeline/queue.py` — simple in-memory job queue with SQLite persistence
- Create `app/pipeline/image_collector.py` — extract and validate image URLs
- Test: `python -m pytest tests/test_pipeline.py`
- Commit: `feat: pipeline orchestrator`

### Phase 5 — FastAPI backend
- Create `app/api/main.py` — FastAPI app, CORS, middleware
- Create `app/api/routes/sources.py` — source management endpoints
- Create `app/api/routes/mine.py` — crawl trigger endpoints
- Create `app/api/routes/pages.py` — page browser endpoints
- Create `app/api/routes/records.py` — record management endpoints
- Create `app/api/routes/images.py` — image endpoints
- Create `app/api/routes/export.py` — export to Artio endpoints
- Create `app/api/routes/stats.py` — dashboard stats
- Test: `python -m pytest tests/test_api.py`
- Commit: `feat: FastAPI backend`

### Phase 6 — React frontend
- Scaffold React app in `frontend/` using Vite + TypeScript
- Install: shadcn/ui, tanstack-query, react-router-dom, lucide-react, axios
- Create pages as specified in `UI.md`
- Create API client in `frontend/src/lib/api.ts`
- Commit: `feat: React admin UI`

### Phase 7 — Export module
- Create `app/export/artio_client.py` — HTTP client for Artio API
- Create `app/export/formatter.py` — format records for Artio feed format
- Test export with mock Artio endpoint
- Commit: `feat: Artio export module`

### Phase 8 — Docker and deployment
- Create `Dockerfile` for the Python backend
- Create `Dockerfile.frontend` for the React frontend
- Create `docker-compose.yml` — runs both services + shared volume for SQLite
- Create `scripts/start.sh` — single command startup
- Commit: `feat: Docker deployment`

---

## Coding Rules

### Python
- Use Python 3.11+
- Use `async/await` throughout — FastAPI async routes, async SQLAlchemy, async httpx
- Use Pydantic v2 for all request/response models
- Use type hints on ALL functions
- Never use `except Exception` without logging — always log the error
- Use `structlog` for all logging — structured JSON output
- All AI calls must have retry logic with exponential backoff (max 3 attempts)
- Never store raw HTML larger than 500KB — truncate before storing
- All database operations must use context managers for sessions

### TypeScript / React
- Strict TypeScript — no `any` types
- Use tanstack-query for all API calls — no raw fetch in components
- Use react-router-dom v6 for routing
- Use shadcn/ui components — do not write custom CSS unless unavoidable
- All forms must have loading states and error handling

### Testing
- Every module must have a corresponding test file
- Use `pytest` with `pytest-asyncio` for async tests
- Use `httpx.AsyncClient` for API tests
- Mock all OpenAI calls in tests — never hit real API in tests
- Minimum: happy path + one error case per function

### Git
- Commit after each phase as specified in Build Order
- Use conventional commits: `feat:`, `fix:`, `test:`, `docs:`
- Never commit `.env` files or `*.db` files
- Never commit `node_modules/` or `__pycache__/`

---

## Environment Variables Required

```
OPENAI_API_KEY=         # Required — OpenAI API key
OPENAI_MODEL=           # Default: gpt-4o
DATABASE_URL=           # Default: sqlite+aiosqlite:///./data/miner.db
ARTIO_API_URL=          # Optional — Artio platform API base URL
ARTIO_API_KEY=          # Optional — Artio platform API key
MAX_CRAWL_DEPTH=        # Default: 3
MAX_PAGES_PER_SOURCE=   # Default: 500
CRAWL_DELAY_MS=         # Default: 1000 (ms between requests)
PLAYWRIGHT_ENABLED=     # Default: true
CORS_ORIGINS=           # Default: http://localhost:5173
```

---

## Verification Steps

After each phase, run the verification command listed in the phase.
After Phase 8, run the full verification:

```bash
# Start services
docker-compose up -d

# Verify API is healthy
curl http://localhost:8000/health

# Verify frontend loads
curl http://localhost:5173

# Run all tests
python -m pytest tests/ -v

# Run a test mine (uses mock, no real OpenAI call)
curl -X POST http://localhost:8000/api/sources \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "name": "Test"}'
```

All checks must pass before marking the build complete.
