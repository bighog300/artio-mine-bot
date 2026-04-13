#!/bin/bash
set -e

echo "Starting Artio Miner..."

# Run database migrations (idempotent — safe to run on every startup)
echo "Running database migrations..."
alembic upgrade head

# Replace this shell process with uvicorn so it becomes PID 1.
# Signals (SIGTERM, SIGINT) are delivered directly to uvicorn for clean shutdown.
echo "Starting API server on :8000..."
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000
