# Artio Miner

A standalone portable web mining application for art-world content.
Point it at any art website and it automatically maps, crawls, extracts,
and manages structured data (artists, events, exhibitions, venues, artworks)
ready for export to the Artio platform.

## Requirements

- Python 3.11+
- Node.js 20+
- OpenAI API key

## Quick Start (Local)

```bash
# Clone and setup
git clone https://github.com/your-org/artio-miner
cd artio-miner

# Copy environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Install Python dependencies
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.api.main:app --reload --port 8000

# In a new terminal — install and start the frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Quick Start (Vercel)

Deploy the API as a serverless function and the frontend as a static site — no
server required.

1. Install the [Vercel CLI](https://vercel.com/docs/cli): `npm i -g vercel`
2. Set the following environment variables in your Vercel project settings:
   - `DATABASE_URL` — required, async PostgreSQL URL using `asyncpg`:
     `postgresql+asyncpg://user:password@host:5432/dbname?sslmode=require`
   - `OPENAI_API_KEY` — required in production
   - `ARTIO_API_URL` / `ARTIO_API_KEY` — optional, for export
   - `CORS_ORIGINS` — your Vercel frontend URL (e.g. `https://artio-miner.vercel.app`)
   - `ENVIRONMENT=production`
3. Deploy: `vercel --prod`

> **Note:** SQLite is blocked in production. Run database migrations via
> `alembic upgrade head` against your production `DATABASE_URL` before deploying.

## Quick Start (Docker)

```bash
cp .env.example .env
# Add your OPENAI_API_KEY to .env

docker compose up
```

Open http://localhost:5173 in your browser.

### Docker build/pull troubleshooting

If `docker compose up --build` fails while pulling base images (for example `nginx:*`), the most common cause is host-side Docker Hub connectivity/rate limiting rather than app code.

```bash
# Verify Docker Hub pull path
docker pull nginx:1.27-alpine

# Authenticate if you hit rate limits
docker login

# Retry clean frontend rebuild
docker compose build frontend --no-cache

# Retry full stack startup
docker compose up --build -d
```

Optional network checks on the deployment host:

```bash
# DNS + TLS reachability to Docker Hub endpoints
nslookup registry-1.docker.io
curl -I https://registry-1.docker.io/v2/
```

## Usage

1. Open the admin UI at http://localhost:5173
2. Click **Add Source** and enter a website URL (e.g. `https://art.co.za`)
3. Click **Add & Start Mining** — the system will:
   - Map the site structure (1-2 minutes)
   - Crawl all art-related sections
   - Extract structured data using GPT-4o
   - Score each record by confidence
4. Browse extracted records in the **Records** section
5. Review, edit, and approve records
6. Export approved records to Artio via **Export**

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Prod | — | OpenAI API key |
| `ENVIRONMENT` | | `development` | Set to `production` for Vercel/serverless mode |
| `OPENAI_MODEL` | | `gpt-4o` | Model to use |
| `DATABASE_URL` | ✅ | `sqlite+aiosqlite:///./data/miner.db` | Async DB URL (`postgresql+asyncpg://...` in production) |
| `ARTIO_API_URL` | | — | Artio platform API URL |
| `ARTIO_API_KEY` | | — | Artio platform API key |
| `MAX_CRAWL_DEPTH` | | `3` | Max link depth |
| `MAX_PAGES_PER_SOURCE` | | `500` | Max pages per crawl |
| `CRAWL_DELAY_MS` | | `1000` | Delay between requests (ms) |
| `PLAYWRIGHT_ENABLED` | | `true` in dev, `false` in prod | Use Playwright for JS sites |
| `CORS_ORIGINS` | | `http://localhost:5173` | Allowed CORS origins |
| `VITE_API_URL` | | `/api` | Frontend API base URL |

## Deployment Checklist

- [ ] Builds without errors
- [ ] `/health` returns `200`
- [ ] Frontend loads and calls `/api`
- [ ] No SQLite in production
- [ ] No long-running tasks in API
- [ ] Env vars required are documented

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Lint
ruff check .

# Format
ruff format .
```

## Architecture

See the specification documents in this repository:
- `SPEC.md` — full product specification and pipeline description
- `SCHEMA.md` — database schema
- `API.md` — API endpoint reference
- `UI.md` — admin UI specification
- `STACK.md` — technology stack and dependencies
- `AGENTS.md` — build instructions for automated scaffolding
