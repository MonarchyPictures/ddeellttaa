# Railway Production Deployment Guide

## Architecture

This application runs as **4 separate services** in Railway:

1. **API Service** - FastAPI web server
2. **Worker Service** - Celery worker for background tasks
3. **Beat Service** - Celery beat for scheduled tasks
4. **Redis** - Message broker (Railway Redis plugin)

## Required Services Configuration

### 1. API Service
- **Builder**: Nixpacks
- **Start Command**: `python -m app.main`
- **Port**: `8000`
- **Health Check Path**: `/health` (or root `/`)

### 2. Worker Service
- **Builder**: Nixpacks (same codebase)
- **Start Command**: `celery -A app.core.celery_app.celery worker --loglevel=info`
- **Port**: None (background worker)

### 3. Beat Service
- **Builder**: Nixpacks (same codebase)
- **Start Command**: `celery -A app.core.celery_app.celery beat --loglevel=info`
- **Port**: None (scheduler only)

### 4. Redis Plugin
- Add the **Redis** plugin from Railway marketplace
- This automatically sets `REDIS_URL` environment variable

## Required Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `DATABASE_URL` | Postgres plugin | PostgreSQL connection string |
| `REDIS_URL` | Redis plugin | Redis connection string |
| `HIGH_RECALL_MODE` | Set manually | Set to `true` for Kenya pipeline |
| `SERPAPI_API_KEY` | Set manually | For Google search API |

## Code Changes Summary

### 1. Celery Configuration (`app/core/celery_app.py`)
- **REMOVED**: SQLite fallback broker
- **REMOVED**: Localhost Redis fallback
- **REMOVED**: Fallback manager and `send_task()` function
- **ADDED**: Hard requirement for `REDIS_URL` - fails loudly if missing

### 2. Celery Worker (`app/core/celery_worker.py`)
- **REMOVED**: All `fallback_manager.register_task()` calls
- **REMOVED**: Sync execution option (`sync=True` parameter)
- **REMOVED**: Direct execution fallbacks
- **CHANGED**: `run_agent_task()` now uses `.delay()` for all platform scrapes
- **CHANGED**: `run_all_agents()` now uses `.delay()` instead of `send_task()`

### 3. API Routes (`app/api/routes/agents.py`)
- **REMOVED**: `/agents/{agent_id}/run-sync` endpoint (no sync execution)
- **REMOVED**: `send_task()` usage
- **CHANGED**: `create_agent()` now uses `run_agent_task.delay()`
- **CHANGED**: `run_agent_now()` now uses `run_agent_task.delay()`

### 4. Search Service (`app/services/search_service.py`)
- **REMOVED**: `ENABLE_CELERY` flag
- **REMOVED**: `send_task("ingest_leads_task", ...)` usage
- **CHANGED**: Now uses `ingest_leads_task.delay()` directly

### 5. Database (`app/db/database.py`)
- **REMOVED**: Default SQLite fallback
- **ADDED**: Hard requirement for `DATABASE_URL` - fails loudly if missing

## Deployment Steps

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Clean Railway production setup - Redis required, no fallbacks"
   git push
   ```

2. **Create services in Railway** (use same GitHub repo for all 3):
   - Create "delta9-api" service with start command `python -m app.main`
   - Create "delta9-worker" service with start command `celery -A app.core.celery_app.celery worker --loglevel=info`
   - Create "delta9-beat" service with start command `celery -A app.core.celery_app.celery beat --loglevel=info`

3. **Add Redis plugin** (creates one Redis instance, shared by all services)

4. **Add Postgres plugin** (if not already present)

5. **Set environment variables**:
   - `HIGH_RECALL_MODE=true`
   - `SERPAPI_API_KEY=your_key_here`

6. **Deploy all services**

## Verification

Check logs for these messages:

**API Service**:
```
MAIN.PY LOADED
Uvicorn running on http://0.0.0.0:8000
```

**Worker Service**:
```
Connected to redis://...
celery@... ready
```

**Beat Service**:
```
beat: Starting...
beat: Acquired lock
```

## Troubleshooting

### "REDIS_URL is not set"
- Make sure Redis plugin is added and deployed
- Check that all services have access to the Redis plugin

### "DATABASE_URL is not set"
- Make sure Postgres plugin is added and deployed
- Check that all services have access to the Postgres plugin

### Railway serving old code
Railway caches aggressively. To force a rebuild:
1. Change the timestamp in `railway.toml` (line: `# Cache buster: 2026-02-27T...`)
2. Push to git
3. Trigger "Redeploy" in Railway UI (select "Clear build cache")

### Worker not processing tasks
- Check Worker service logs for connection errors
- Verify `REDIS_URL` is accessible from Worker service
- Check that tasks are being queued: look for "Queued X leads" in API logs

## Local Development

For local development with SQLite:

```bash
export DATABASE_URL="sqlite:///./local.db"
export REDIS_URL="redis://localhost:6379/0"
export HIGH_RECALL_MODE="true"
export SERPAPI_API_KEY="your_key"

# Terminal 1: API
python -m app.main

# Terminal 2: Worker
celery -A app.core.celery_app.celery worker --loglevel=info

# Terminal 3: Beat (optional - for scheduled tasks)
celery -A app.core.celery_app.celery beat --loglevel=info
```
