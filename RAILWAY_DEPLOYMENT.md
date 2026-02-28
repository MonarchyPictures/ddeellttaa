# Railway Production Deployment Guide

## Quick Start (Automated)

```bash
# Make script executable
chmod +x railway-setup.sh

# Run setup script
./railway-setup.sh
```

## Manual Setup (Step-by-Step)

### Prerequisites

- Railway CLI installed: `npm install -g @railway/cli`
- Logged in: `railway login`
- Project created at https://railway.app

---

## Step 1: Create Redis Plugin

```bash
railway add --plugin redis
```

This automatically creates:
- Redis instance
- `REDIS_URL` environment variable (available to all services)

---

## Step 2: Create PostgreSQL Database

```bash
railway add --plugin postgres
```

This automatically creates:
- PostgreSQL database
- `DATABASE_URL` environment variable (available to all services)

---

## Step 3: Create Services

Create 3 services from the same GitHub repo:

```bash
# API Service
railway service create delta9-api

# Worker Service
railway service create delta9-worker

# Beat Service
railway service create delta9-beat
```

---

## Step 4: Configure Start Commands

In Railway dashboard (https://railway.app/dashboard):

### API Service (`delta9-api`)
```
Start Command: python -m app.main
Port: 8000
```

### Worker Service (`delta9-worker`)
```
Start Command: celery -A app.core.celery_app.celery worker --loglevel=info
```

### Beat Service (`delta9-beat`)
```
Start Command: celery -A app.core.celery_app.celery beat --loglevel=info
```

---

## Step 5: Set Environment Variables

Set these for **all services**:

```bash
railway variables set HIGH_RECALL_MODE=true
railway variables set SCRAPER_CONCURRENCY=3
railway variables set CACHE_TTL_SECONDS=600
railway variables set SCRAPER_TIMEOUT_SECONDS=25
railway variables set TOTAL_PHASE_TIMEOUT_SECONDS=60
railway variables set SERPAPI_API_KEY=your_key_here
```

Or via Railway dashboard:
- Go to each service → Variables tab
- Add variables (they inherit from project level)

---

## Step 6: Connect Services to Plugins

In Railway dashboard:

1. Go to each service (API, Worker, Beat)
2. Click "Settings" → "Service Connections"
3. Connect to:
   - Redis plugin
   - PostgreSQL plugin

This ensures `REDIS_URL` and `DATABASE_URL` are available.

---

## Step 7: Deploy

```bash
railway up
```

Or deploy via Railway dashboard:
- Click "Deploy" on each service

---

## Verification

### Check API is running
```bash
curl https://your-app.railway.app/health
curl https://your-app.railway.app/api/agents/
```

### Check Worker logs
```bash
railway logs --service delta9-worker
```

Expected output:
```
Connected to redis://...
celery@... ready
Task app.core.celery_worker.run_agent_task[...] succeeded
```

### Check Beat logs
```bash
railway logs --service delta9-beat
```

Expected output:
```
beat: Starting...
beat: Acquired lock
```

### Check Redis connection
```bash
railway logs --service delta9-api
```

Look for:
```
Redis cache connected. TTL: 600s
```

---

## Troubleshooting

### "REDIS_URL is not set"
```bash
# Check Redis plugin is connected
railway status

# Check environment variables
railway variables
```

### "DATABASE_URL is not set"
```bash
# Check PostgreSQL plugin is connected
railway status
```

### Worker not processing tasks
```bash
# Check Worker logs
railway logs --service delta9-worker --follow

# Verify Redis connection
# Should show: Connected to redis://...
```

### "Module not found"
```bash
# Rebuild and redeploy
railway up --build
```

### Railway serving old code
```bash
# Force rebuild
railway up --build

# Or in dashboard: "Redeploy" with "Clear build cache"
```

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   API       │────▶│   Worker    │────▶│    Redis    │
│  (FastAPI)  │     │  (Celery)   │     │  (Broker)   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌─────────────┐      ┌─────────────┐
                    │    Beat     │      │    Cache    │
                    │  (Scheduler)│      │             │
                    └─────────────┘      └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  PostgreSQL │
                    │  (Database) │
                    └─────────────┘
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Auto | - | From Redis plugin |
| `DATABASE_URL` | Auto | - | From PostgreSQL plugin |
| `HIGH_RECALL_MODE` | Yes | - | Set to `true` for Kenya pipeline |
| `SCRAPER_CONCURRENCY` | No | 3 | Max concurrent scrapers (max 4) |
| `CACHE_TTL_SECONDS` | No | 600 | Cache TTL in seconds |
| `SCRAPER_TIMEOUT_SECONDS` | No | 25 | Per-scraper timeout |
| `TOTAL_PHASE_TIMEOUT_SECONDS` | No | 60 | Total scraping timeout |
| `SERPAPI_API_KEY` | Yes | - | SerpAPI key |

---

## Scaling

### Increase Concurrency (Paid Tier)
```bash
railway variables set SCRAPER_CONCURRENCY=4
```

### Add More Workers
Scale horizontally by increasing Worker service instances in Railway dashboard.

---

## Monitoring

### View Logs
```bash
# All services
railway logs

# Specific service
railway logs --service delta9-api
railway logs --service delta9-worker
railway logs --service delta9-beat
```

### View Metrics
In Railway dashboard:
- CPU usage
- Memory usage
- Request count
- Error rate

---

## Local Development

```bash
# Set environment
export DATABASE_URL="sqlite:///./local.db"
export REDIS_URL="redis://localhost:6379/0"
export HIGH_RECALL_MODE="true"
export SCRAPER_CONCURRENCY="3"

# Terminal 1: API
python -m app.main

# Terminal 2: Worker
celery -A app.core.celery_app.celery worker --loglevel=info

# Terminal 3: Beat
celery -A app.core.celery_app.celery beat --loglevel=info
```

---

## Support

- Railway Docs: https://docs.railway.app
- Celery Docs: https://docs.celeryproject.org
- FastAPI Docs: https://fastapi.tiangolo.com
