# Delta-9 Distributed Scraper Workers

Architecture: **FastAPI + Celery + Redis + Multiple Workers**

## Overview

Instead of scraping in the API process, we use distributed workers:

```
User Search
     │
     ▼
API (FastAPI) ──► Redis Queue
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   Reddit Worker  Twitter Worker  Forum Worker
        │             │             │
        └─────────────┴─────────────┘
                      │
                      ▼
                Lead Database
```

## Quick Start

### 1. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or locally
redis-server
```

### 2. Start Workers

```bash
# Option 1: Using Python script
python start_workers.py

# Option 2: Using Docker Compose (recommended)
docker-compose up -d

# Option 3: Manual Celery commands
# Terminal 1: Scraper workers
celery -A app.core.celery_config.celery_app worker -Q scrapers -n scraper@%h --loglevel=info

# Terminal 2: Default queue
celery -A app.core.celery_config.celery_app worker -Q default -n default@%h --loglevel=info

# Terminal 3: High priority queue
celery -A app.core.celery_config.celery_app worker -Q high_priority -n high@%h --loglevel=info
```

### 3. Start API

```bash
uvicorn app.main:app --reload
```

## API Endpoints

### Async Search (Distributed)

```bash
# Launch distributed search
POST /api/search/async
{
  "query": "plumber",
  "expand": true
}

# Response:
{
  "workflow": "distributed_search",
  "query": "plumber",
  "task_id": "abc-123",
  "status": "queued",
  "poll_url": "/api/tasks/abc-123/status"
}
```

### Check Task Status

```bash
GET /api/tasks/{task_id}/status

# Response:
{
  "task_id": "abc-123",
  "status": "SUCCESS",  # PENDING, STARTED, SUCCESS, FAILURE
  "ready": true,
  "successful": true,
  "result": {...}
}
```

### Single Source Search

```bash
POST /api/search/source/reddit
{
  "query": "crm software"
}
```

### Worker Status

```bash
GET /api/workers/status
GET /api/workers/ping
GET /api/queues/status
```

## Task Queues

| Queue | Purpose | Workers |
|-------|---------|---------|
| `scrapers` | Reddit, Twitter, Forum scraping | 2-4 workers |
| `high_priority` | Critical tasks, bulk operations | 2-4 workers |
| `default` | General tasks, lead processing | 1-2 workers |
| `low_priority` | Background enrichment | 1 worker |

## Celery Tasks

### Scraper Tasks

```python
# Scrape single source
scrape_reddit.delay("plumber")
scrape_twitter.delay("plumber")
scrape_forum.delay("plumber")

# Scrape all sources in parallel
scrape_all_sources.delay("plumber", expand=True)

# Full workflow
search_and_process.delay("plumber", expand=True)
```

### Lead Tasks

```python
# Create lead from signals
create_lead_from_signals.delay([1, 2, 3])

# Verify lead data
verify_lead.delay(lead_id=1)

# Enrich lead
enrich_lead_data.delay(lead_id=1)
```

## Monitoring

### Flower (Celery Web UI)

```bash
celery -A app.core.celery_config.celery_app flower --port=5555
```

Open http://localhost:5555

### Health Check

```bash
GET /health

{
  "status": "ok",
  "celery": {
    "status": "ok",
    "redis": "connected"
  }
}
```

## Railway Deployment

### 1. Add Redis to Railway

```bash
railway add --database redis
```

### 2. Deploy Services

Railway will read the `Procfile` and deploy:
- `web`: FastAPI application
- `worker`: Celery workers
- `beat`: Scheduled tasks

### 3. Scale Workers

```bash
# Scale to 3 workers
railway scale worker=3
```

## Environment Variables

```bash
# Required
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///./delta9.db

# Optional
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Architecture Benefits

1. **Scalability**: Add more workers as needed
2. **Reliability**: Failed tasks auto-retry with backoff
3. **Rate Limiting**: Control request rates per source
4. **Queue Prioritization**: High-priority tasks first
5. **Monitoring**: Track task progress and worker health
6. **Background Processing**: API stays responsive

## Troubleshooting

### Workers not starting

```bash
# Check Redis connection
python -c "from app.core.celery_config import check_celery_health; print(check_celery_health())"
```

### Task stuck in PENDING

```bash
# Check worker status
celery -A app.core.celery_config.celery_app inspect active

# Purge stuck tasks
celery -A app.core.celery_config.celery_app purge
```

### Rate limiting errors

```bash
# Check rate limits
celery -A app.core.celery_config.celery_app inspect scheduled
```
