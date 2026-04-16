#!/usr/bin/env bash
set -euo pipefail

echo "📥 Pulling latest code from GitHub..."
git pull origin main

echo "🛑 Stopping running containers..."
docker compose down

echo "🔨 Rebuilding images..."
docker compose build

echo "🗄️ Running migrations..."
docker compose run --rm migrate alembic upgrade head

echo "🚀 Starting containers..."
docker compose up -d

echo "📊 Checking container status..."
docker compose ps

echo "📜 Showing recent logs (migrate)..."
docker compose logs migrate --tail=50

echo "✅ Update complete"
