# Codex Brief: Repo Hardening and Documentation Alignment

## Objective

Apply a small, high-confidence maintenance pass that fixes known deployment and routing problems, makes local development CORS behavior correct for browser clients, and rewrites the repository README so it matches the code that actually exists.

This is a narrow cleanup task. Do not redesign the app, rename major modules, or change product behavior beyond the explicit fixes below.

---

## Scope

Make only these changes:

1. Fix `vercel.json` so it is valid JSON.
2. Fix `deploy.sh` so its host URLs and migration invocation match `docker-compose.yml`.
3. Remove the duplicate metrics router registration from `app/api/main.py`.
4. Fix dev CORS in `app/api/main.py` so it works with `allow_credentials=True`.
5. Rewrite `README.md` so it describes the current repository instead of an outdated backfill-only view.

Do not bundle unrelated refactors into this task.

---

## Repository facts to preserve

- Backend entrypoint: `app/api/main.py`
- Host API port in Docker Compose: `8765`
- Container API port: `8000`
- Frontend host port in Docker Compose: `5173`
- Migration service name in Compose: `migrate`
- Compose file does **not** define any `profiles:` entries.
- Existing docs live primarily under `docs/root/` and `docs/backfill/`.

---

## Required changes

### 1) `vercel.json`

The current file is not valid JSON because it contains comments and an ellipsis placeholder.

Requirements:
- Output must be parseable JSON.
- Keep the existing intent:
  - frontend build command
  - frontend output directory
  - Python runtime config for `api/index.py`
- Remove all inline comments and placeholders.
- Preserve the currently intended memory and duration values unless there is a clear repo-local reason not to.

A valid target shape is roughly:

```json
{
  "buildCommand": "cd frontend && npm install && VITE_API_URL= npm run build",
  "outputDirectory": "frontend/dist",
  "functions": {
    "api/index.py": {
      "runtime": "vercel-python@4.1.4",
      "memory": 3008,
      "maxDuration": 60
    }
  }
}
```

If Vercel requires additional fields for this repo, keep them valid JSON as well.

### 2) `deploy.sh`

Make the script consistent with `docker-compose.yml`.

Required fixes:
- Health check loop must probe `http://localhost:8765/health`, not `:8000`.
- Final printed API and health URLs must use host port `8765`.
- Migration command must not use `--profile migrate` because no compose profile exists.
- Prefer:
  ```bash
  $COMPOSE run --rm migrate
  ```
- Do not change unrelated deploy semantics in this task.

### 3) Duplicate metrics router registration

In `app/api/main.py`, the metrics router is included twice: once with the `/api` prefix and once without.

Requirements:
- Keep only one registration.
- Prefer the namespaced registration under `/api` unless another in-repo route contract clearly depends on `/metrics`.
- Do not remove the route module itself.

### 4) Development CORS

Current behavior uses:
- `allow_origins=["*"]`
- `allow_credentials=True`

That combination is incorrect for browser credentialed requests.

Requirements:
- In development / non-serverless mode, use explicit origins instead of `"*"`.
- Base the origin list on `settings.cors_origins`.
- It is acceptable to provide a reasonable fallback list such as:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
  - optionally local API origins if needed
- Preserve stricter production/serverless behavior.
- Keep `allow_credentials=True` only if origins are explicit.

Implementation preference:
- Centralize origin parsing into a small helper or clear expression.
- Strip whitespace and ignore empty entries.

### 5) `README.md`

Replace the current backfill-phase README with one that matches the actual repository.

The new README should:
- Describe the repo as **Artio Miner**, not only the backfill subsystem.
- Explain the backend, frontend, worker, migration, and docs structure at a high level.
- Point to real files that exist in the repo.
- Include setup instructions that work with the current layout.
- Use the real local ports:
  - API: `http://localhost:8765`
  - Frontend: `http://localhost:5173`
- Mention that the API container listens internally on `8000`, but Docker exposes it on `8765`.
- Include common commands for:
  - install backend deps
  - install frontend deps
  - run tests
  - run Docker Compose
  - run migrations
- Link to existing docs under:
  - `docs/root/`
  - `docs/backfill/`
- Remove broken references to missing root-level phase docs.
- Remove examples that import `async_session` from `app.db` unless you also add that export in this task.

Keep the README practical and concise. Prefer accuracy over marketing language.

---

## Acceptance criteria

The task is complete when all of the following are true:

- `python -m json.tool vercel.json` succeeds.
- `deploy.sh` no longer references host port `8000` for the API or health URL.
- `deploy.sh` no longer uses `--profile migrate`.
- `app/api/main.py` includes the metrics router only once.
- Development CORS no longer uses `allow_origins=["*"]` together with `allow_credentials=True`.
- `README.md` contains only working, in-repo file references for its primary documentation links.
- README setup commands match current ports and file layout.

---

## Files expected to change

- `vercel.json`
- `deploy.sh`
- `app/api/main.py`
- `README.md`

Potentially acceptable if needed:
- a small helper in `app/api/main.py`
- no other files unless necessary to keep docs accurate

---

## Non-goals

Do not do the following as part of this task unless strictly required by one of the scoped fixes:
- redesign deployment strategy
- rewrite Docker Compose
- add new services
- change route shapes beyond removing the accidental duplicate metrics exposure
- refactor business logic
- add unrelated linting or formatting work

---

## Suggested verification commands

```bash
python -m json.tool vercel.json

python -m compileall app

grep -n "localhost:8000" deploy.sh || true

grep -n -- "--profile migrate" deploy.sh || true

python - <<'PY'
from pathlib import Path
p = Path('app/api/main.py').read_text()
print(p.count('metrics_routes.router'))
PY
```

If dependencies are installed, also run:

```bash
pytest -q tests/test_config.py tests/test_api.py
```
