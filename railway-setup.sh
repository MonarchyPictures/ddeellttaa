#!/bin/bash
# Railway Setup Script
# Run these commands to set up the complete Railway infrastructure

set -e

echo "========================================"
echo "Delta-9 Railway Production Setup"
echo "========================================"
echo ""

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Install with:"
    echo "   npm install -g @railway/cli"
    exit 1
fi

echo "✅ Railway CLI found"
echo ""

# Login check
echo "Checking Railway login..."
railway whoami || (echo "❌ Not logged in. Run: railway login" && exit 1)
echo ""

# Link to project (or create new)
echo "Linking to Railway project..."
echo "If you don't have a project, create one first at https://railway.app"
read -p "Press Enter to continue or Ctrl+C to cancel..."
railway link
echo ""

echo "========================================"
echo "Step 1: Creating Redis Plugin"
echo "========================================"
railway add --plugin redis
echo "✅ Redis plugin added"
echo ""

echo "========================================"
echo "Step 2: Creating Database"
echo "========================================"
railway add --plugin postgres
echo "✅ PostgreSQL database added"
echo ""

echo "========================================"
echo "Step 3: Creating API Service"
echo "========================================"
railway service create delta9-api
echo "✅ API service created"
echo ""

echo "========================================"
echo "Step 4: Creating Worker Service"
echo "========================================"
railway service create delta9-worker
echo "✅ Worker service created"
echo ""

echo "========================================"
echo "Step 5: Creating Beat Service"
echo "========================================"
railway service create delta9-beat
echo "✅ Beat service created"
echo ""

echo "========================================"
echo "Step 6: Setting Environment Variables"
echo "========================================"

# Set variables for all services
echo "Setting HIGH_RECALL_MODE=true..."
railway variables set HIGH_RECALL_MODE=true

echo "Setting SCRAPER_CONCURRENCY=3..."
railway variables set SCRAPER_CONCURRENCY=3

echo "Setting CACHE_TTL_SECONDS=600..."
railway variables set CACHE_TTL_SECONDS=600

echo "Setting SCRAPER_TIMEOUT_SECONDS=25..."
railway variables set SCRAPER_TIMEOUT_SECONDS=25

echo "Setting TOTAL_PHASE_TIMEOUT_SECONDS=60..."
railway variables set TOTAL_PHASE_TIMEOUT_SECONDS=60

echo "✅ Environment variables set"
echo ""

echo "========================================"
echo "Step 7: Configuring Service Commands"
echo "========================================"

echo ""
echo "⚠️  MANUAL STEP REQUIRED:"
echo ""
echo "1. Go to https://railway.app/dashboard"
echo "2. Select your project"
echo "3. Configure each service:"
echo ""
echo "   API Service (delta9-api):"
echo "   - Start Command: python -m app.main"
echo "   - Port: 8000"
echo ""
echo "   Worker Service (delta9-worker):"
echo "   - Start Command: celery -A app.core.celery_app.celery worker --loglevel=info"
echo ""
echo "   Beat Service (delta9-beat):"
echo "   - Start Command: celery -A app.core.celery_app.celery beat --loglevel=info"
echo ""
echo "4. Ensure Redis and PostgreSQL plugins are connected to all services"
echo ""
read -p "Press Enter after configuring services in Railway dashboard..."
echo ""

echo "========================================"
echo "Step 8: Deploying All Services"
echo "========================================"
railway up
echo ""

echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo "Services deployed:"
echo "  - API: https://your-app.railway.app"
echo "  - Worker: Background task processor"
echo "  - Beat: Scheduled task scheduler"
echo "  - Redis: Message broker & cache"
echo "  - PostgreSQL: Database"
echo ""
echo "Monitor logs:"
echo "  railway logs --service delta9-api"
echo "  railway logs --service delta9-worker"
echo "  railway logs --service delta9-beat"
echo ""
