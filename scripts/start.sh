#!/bin/bash
set -e

echo "Starting Artio Miner API..."

# Print sanitized DATABASE_URL for debugging container env mismatches.
python - <<'PY'
from app.config import sanitize_database_url, settings
print(f"DATABASE_URL={sanitize_database_url(settings.database_url)}")
PY

echo "Running database migrations (alembic upgrade head)..."
alembic upgrade head

echo "Starting API server on :8000..."
exec "$@"
