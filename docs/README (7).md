# Artio Miner

Artio Miner is a FastAPI + React application for crawling art-related websites, classifying pages, extracting structured entities, reviewing mined records, and exporting data to Artio-compatible systems. The repository also contains worker, queue, source-mapper, and backfill components used to run mining and enrichment workflows.

## What is in this repo

### Backend
- `app/api/` — FastAPI app, middleware, auth, schemas, and route modules
- `app/db/` — SQLAlchemy models, database setup, CRUD helpers, and Alembic environment
- `app/crawler/` — fetchers, site mapping, robots support, and crawl helpers
- `app/ai/` — classification, extraction, confidence, and model client logic
- `app/pipeline/` — pipeline runner, queue helpers, job progress, and backfill processors
- `app/source_mapper/` — source-mapper proposal and preview logic
- `app/export/` — export client and formatting utilities
- `app/cli/` — command-line tools, including backfill commands

### Frontend
- `frontend/` — Vite + React + TypeScript admin UI

### Deployment and operations
- `docker-compose.yml` — local multi-service stack
- `deploy.sh` — deployment helper script
- `scripts/start.sh` — backend container startup wrapper
- `vercel.json` — Vercel configuration for the frontend/serverless deployment path

### Tests
- `tests/` — backend test suite

### Documentation
- `docs/root/` — main product, API, schema, stack, deploy, and implementation docs
- `docs/backfill/` — backfill-specific guides and phase docs
- `docs/audit/reports/` — repository audits and verification notes

## Repo layout

```text
.
├── app/
│   ├── ai/
│   ├── api/
│   ├── cli/
│   ├── crawler/
│   ├── db/
│   ├── export/
│   ├── extraction/
│   ├── metrics/
│   ├── pipeline/
│   ├── services/
│   └── source_mapper/
├── frontend/
├── tests/
├── docs/
├── docker-compose.yml
├── deploy.sh
├── pyproject.toml
└── vercel.json
```

## Requirements

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose for the local stack
- PostgreSQL and Redis if you are running services outside Docker
- `OPENAI_API_KEY` for AI-backed extraction flows

## Environment setup

Copy the sample environment file:

```bash
cp .env.example .env
```

Important values:
- `DATABASE_URL` should use the async SQLAlchemy form, for example `postgresql+asyncpg://...`
- `CORS_ORIGINS` is a comma-separated list of allowed frontend origins
- In Docker, the backend container listens on `8000`, but Docker exposes the API on host port `8765`

## Local development

### Backend

Install backend dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the API locally:

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

If you run the backend directly instead of through Docker, the API will be available on `http://localhost:8000` unless you choose a different port.

### Frontend

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run the frontend dev server:

```bash
npm run dev
```

The frontend dev server defaults to `http://localhost:5173`.

## Docker Compose

Start the full local stack:

```bash
docker compose up -d
```

Services exposed on the host:
- Frontend: `http://localhost:5173`
- API: `http://localhost:8765`
- API health: `http://localhost:8765/health`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

View running services:

```bash
docker compose config --services
```

Stop the stack:

```bash
docker compose down
```

## Migrations

Run database migrations in Docker:

```bash
docker compose run --rm migrate
```

There is also a helper target:

```bash
make migrate
```

## Tests

Run the backend tests:

```bash
pytest -q
```

Run a smaller subset while iterating:

```bash
pytest -q tests/test_config.py tests/test_api.py
```

Run frontend tests:

```bash
cd frontend
npm test
```

## Useful commands

```bash
make services     # list compose services
make up           # start the stack
make down         # stop the stack
make logs-migrate # inspect migration logs
make routes       # print backend routes
```

## Key docs

Primary repo docs:
- `docs/root/SPEC.md`
- `docs/root/SCHEMA.md`
- `docs/root/API.md`
- `docs/root/UI.md`
- `docs/root/STACK.md`
- `docs/root/DEPLOY.md`
- `docs/root/QUICK_START.md`

Backfill docs:
- `docs/backfill/README.md`
- `docs/backfill/phases/PHASE_1_FOUNDATION.md`
- `docs/backfill/phases/PHASE_2_WORKER.md`
- `docs/backfill/phases/PHASE_3_SCHEDULING.md`
- `docs/backfill/phases/PHASE_4_DASHBOARD.md`

Maintenance docs added for the current cleanup task:
- `docs/root/CODEX_REPO_HARDENING_BRIEF.md`
- `docs/root/CODEX_REPO_HARDENING_CHECKLIST.md`
- `docs/root/CODEX_REPO_HARDENING_PROMPT.txt`

## Notes

- The repo contains both the general mining platform and backfill-specific subsystems.
- Some docs under `docs/root/` are historical implementation records; prefer the files listed above when onboarding.
- Vercel and Docker are both present in the repo, but they serve different deployment paths.
