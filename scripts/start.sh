#!/bin/bash
set -e

echo "Starting Artio Miner..."

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start API in background
echo "Starting API server..."
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &

echo "Artio Miner API running on http://localhost:8000"
echo "Open the admin UI at http://localhost:5173"

wait
