#!/bin/bash
set -e

echo "🧪 Testing Fresh Deployment from Scratch"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup
echo "📦 Cleaning up existing deployment..."
docker-compose down -v >/dev/null 2>&1
docker volume rm artio-mine-bot_postgres_data >/dev/null 2>&1 || true
echo "✅ Cleanup complete"
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start services${NC}"
    exit 1
fi
echo "✅ Services started"
echo ""

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 20
echo "✅ PostgreSQL should be ready"
echo ""

# Run migrations
echo "🗄️  Running database migrations..."
docker-compose exec -T api alembic upgrade head
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Migrations failed!${NC}"
    echo ""
    echo "Logs:"
    docker-compose logs api | tail -50
    exit 1
fi
echo "✅ Migrations completed successfully"
echo ""

# Check migration status
echo "📊 Checking migration status..."
MIGRATION_STATUS=$(docker-compose exec -T api alembic current 2>&1)
echo "$MIGRATION_STATUS"
echo ""

# Test API
echo "🔌 Testing API endpoints..."

# Test sources endpoint
SOURCES_RESPONSE=$(curl -s http://localhost:8765/api/sources)
if echo "$SOURCES_RESPONSE" | grep -q "items"; then
    echo -e "${GREEN}✅ /api/sources responding correctly${NC}"
else
    echo -e "${RED}❌ /api/sources not responding correctly${NC}"
    echo "Response: $SOURCES_RESPONSE"
    exit 1
fi

# Test health endpoint
HEALTH_RESPONSE=$(curl -s http://localhost:8765/api/health || echo "failed")
if echo "$HEALTH_RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}✅ /api/health responding correctly${NC}"
else
    echo -e "${YELLOW}⚠️  /api/health not responding (may not exist)${NC}"
fi
echo ""

# Test frontend
echo "🎨 Testing frontend..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173)
if [ "$FRONTEND_STATUS" == "200" ]; then
    echo -e "${GREEN}✅ Frontend accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend returned status: $FRONTEND_STATUS${NC}"
fi
echo ""

# Check tables exist
echo "🗃️  Verifying database tables..."
TABLES=$(docker-compose exec -T db psql -U postgres -d artio -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';" 2>/dev/null | tr -d ' ')
if [ "$TABLES" -gt 15 ]; then
    echo -e "${GREEN}✅ Database has $TABLES tables${NC}"
else
    echo -e "${RED}❌ Expected 15+ tables, found $TABLES${NC}"
    exit 1
fi
echo ""

# Final status
echo "========================================"
echo -e "${GREEN}🎉 Fresh Deployment Successful!${NC}"
echo ""
echo "📍 Access Points:"
echo "   Frontend: http://localhost:5173"
echo "   API: http://localhost:8765"
echo "   API Docs: http://localhost:8765/docs"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "✅ All checks passed. Application ready to use!"
