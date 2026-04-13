#!/bin/sh
# Replaces the hardcoded API base URL in Vite-built JS assets with the value
# of $VITE_API_URL at container start time.
#
# This lets a single pre-built Docker image target any backend without rebuild.
# Placed in /docker-entrypoint.d/ so the official nginx image runs it before
# starting nginx.
set -e

REPLACE_FROM="http://localhost:8000"
REPLACE_TO="${VITE_API_URL:-}"

if [ -z "$REPLACE_TO" ]; then
    echo "[inject-api-url] VITE_API_URL not set — keeping default ($REPLACE_FROM)"
    exit 0
fi

# Strip trailing slash to match the hardcoded form
REPLACE_TO="${REPLACE_TO%/}"

if [ "$REPLACE_FROM" = "$REPLACE_TO" ]; then
    echo "[inject-api-url] VITE_API_URL matches default, nothing to replace"
    exit 0
fi

echo "[inject-api-url] Replacing $REPLACE_FROM → $REPLACE_TO"
find /usr/share/nginx/html -name "*.js" -exec \
    sed -i "s|${REPLACE_FROM}|${REPLACE_TO}|g" {} +
echo "[inject-api-url] Done"
