# Artio Miner

Artio Miner is a full-stack repository for crawling art-focused websites, extracting structured data, reviewing mined records, and exporting approved data to Artio.

## Repository layout

- `app/api/main.py` — FastAPI backend entrypoint.
- `app/` — backend services (API routes, crawler, AI extraction, DB models, queue/pipeline, export).
- `frontend/` — React + Vite admin UI.
- `app/pipeline/runner.py` — background worker runner used by worker containers.
- `alembic/` + `alembic.ini` — migration configuration.
- `docker-compose.yml` — local multi-service stack (API, frontend, Postgres, Redis, workers, migrate job).
- `docs/root/` — primary product, API, UI, stack, and delivery docs.
- `docs/backfill/` — backfill subsystem docs.

## Local ports

When running with Docker Compose:

- Frontend (host): `http://localhost:5173`
- API (host): `http://localhost:8765`
- API health (host): `http://localhost:8765/health`

Inside containers, the API listens on port `8000` and is published to host port `8765`.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose
- A `.env` file (copy from `.env.example`)

## Local development (without Docker)

### 1) Install backend dependencies

```bash
python -m pip install -e ".[dev]"
```

### 2) Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 3) Run DB migrations

```bash
alembic upgrade head
```

### 4) Run backend API

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8765
```

### 5) Run frontend

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

## Docker Compose workflow

### Start full stack

```bash
docker compose up -d --build
```

### Run migrations manually

```bash
docker compose run --rm migrate
```

### Stop stack

```bash
docker compose down
```

## Testing

Run backend tests:

```bash
pytest -q
```

Run frontend tests:

```bash
cd frontend
npm test
```

## Documentation

- Core repository documentation: `docs/root/`
  - Start with `docs/root/SPEC.md`, `docs/root/API.md`, `docs/root/UI.md`, `docs/root/STACK.md`
- Backfill documentation: `docs/backfill/`
  - Start with `docs/backfill/README.md`
