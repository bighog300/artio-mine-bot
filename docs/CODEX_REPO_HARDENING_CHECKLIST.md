# Repo Hardening Checklist

Use this checklist while implementing the repo maintenance fixes.

## Patch checklist

- [ ] `vercel.json` is valid JSON with no comments or placeholders.
- [ ] `vercel.json` still points to `frontend/dist`.
- [ ] `vercel.json` still configures `api/index.py` with the intended Python runtime.
- [ ] `deploy.sh` health probe uses `http://localhost:8765/health`.
- [ ] `deploy.sh` summary prints API URL as `http://localhost:8765`.
- [ ] `deploy.sh` summary prints health URL as `http://localhost:8765/health`.
- [ ] `deploy.sh` runs migrations with `docker compose run --rm migrate` semantics.
- [ ] `app/api/main.py` includes the metrics router only once.
- [ ] Dev CORS uses explicit origins, not `"*"`.
- [ ] CORS origin parsing strips whitespace and ignores empty values.
- [ ] `README.md` describes the whole repo, not just the backfill subsystem.
- [ ] `README.md` references existing docs paths only.
- [ ] `README.md` uses the correct Docker host ports.
- [ ] `README.md` does not rely on `from app.db import async_session` examples.

## Quick grep checks

```bash
grep -n "localhost:8000" deploy.sh README.md || true
grep -n -- "--profile migrate" deploy.sh || true
grep -n "metrics_routes.router" app/api/main.py
```

## JSON validation

```bash
python -m json.tool vercel.json >/dev/null
```

## Sanity checks

```bash
python -m compileall app
```
