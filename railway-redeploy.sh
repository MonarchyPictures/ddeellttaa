#!/bin/bash
# Railway Force Redeploy Script with Cache Clear

set -e

echo "============================================================"
echo "Railway Force Redeploy with Cache Clear"
echo "============================================================"
echo ""

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found"
    echo "Install with: npm install -g @railway/cli"
    exit 1
fi

echo "✅ Railway CLI found"

# Check login
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway"
    echo "Run: railway login"
    exit 1
fi

echo "✅ Logged in to Railway"
echo ""

# Link to project if not already linked
if [ ! -f .railway/config.json ]; then
    echo "Linking to Railway project..."
    railway link
fi

echo "============================================================"
echo "Step 1: Pushing new commit to trigger build"
echo "============================================================"
echo ""

# Make a cache-busting commit
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
echo "# Cache buster: $TIMESTAMP" >> README.md
git add README.md
git commit -m "Force redeploy: cache clear $TIMESTAMP" || true
git push origin HEAD

echo "✅ Code pushed"
echo ""

echo "============================================================"
echo "Step 2: Deploying to Railway (with cache clear)"
echo "============================================================"
echo ""

# Deploy with build
railway up --build

echo "✅ Deployed"
echo ""

echo "============================================================"
echo "Step 3: Checking logs for new version"
echo "============================================================"
echo ""

echo "Checking API service logs for VERSION string..."
railway logs --service delta9-api | grep -E "(VERSION|HIGH-RECALL|RAILWAY DEPLOY)" | head -5 || true

echo ""
echo "============================================================"
echo "Step 4: Running verification checks"
echo "============================================================"
echo ""

python3 verify-deployment.py || true

echo ""
echo "============================================================"
echo "COMPLETE"
echo "============================================================"
echo ""
echo "To monitor logs:"
echo "  railway logs --service delta9-api --follow"
echo ""
echo "To check all services:"
echo "  railway status"
echo ""
