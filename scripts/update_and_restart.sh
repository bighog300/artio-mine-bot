#!/usr/bin/env bash

set -euo pipefail

echo "🚀 Starting Artio update..."

PROJECT_DIR="$HOME/artio-mine-bot"

cd "$PROJECT_DIR"

echo "📥 Pulling latest code..."
git pull origin main

echo "🛑 Stopping app containers (keeping DB + Redis)..."
docker compose stop api frontend worker-1 worker-2 worker-3 worker-4 worker-5

echo "🔨 Rebuilding containers..."
docker compose build api frontend worker-1 worker-2 worker-3 worker-4 worker-5

echo "🚀 Starting API..."
docker compose up -d api

echo "⏳ Waiting for API to boot..."
sleep 5

echo "🗄 Running migrations..."
docker compose exec -T api alembic upgrade head

echo "🧵 Starting workers + frontend..."
docker compose up -d worker-1 worker-2 worker-3 worker-4 worker-5 frontend

echo "✅ Deployment complete!"

echo ""
echo "📊 Container status:"
docker compose ps

echo ""
echo "🔍 Health check:"
curl -s http://localhost:8765/health || echo "⚠️ API not responding yet"
