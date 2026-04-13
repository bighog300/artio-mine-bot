#!/bin/bash
set -e

echo "Starting Artio Miner..."

# Print sanitized DATABASE_URL for debugging container env mismatches.
python - <<'PY'
from app.config import sanitize_database_url, settings
print(f"DATABASE_URL={sanitize_database_url(settings.database_url)}")
PY

# Run database migrations with retries so app doesn't crash if DB is still booting.
max_attempts=10
attempt=1
until alembic upgrade head; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Migration failed after ${max_attempts} attempts."
    exit 1
  fi
  echo "Migration attempt ${attempt}/${max_attempts} failed, retrying in 3s..."
  attempt=$((attempt + 1))
  sleep 3
done

echo "Starting API server on :8000..."
exec "$@"
