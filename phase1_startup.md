# Phase 1 — Startup & Runtime Reliability

Ensure API waits for DB, retries, logs clearly, and fails deterministically.

## Tasks
- Add DB retry loop (max 30 attempts)
- Fail fast on migration errors
- Use exec uvicorn for signal handling
