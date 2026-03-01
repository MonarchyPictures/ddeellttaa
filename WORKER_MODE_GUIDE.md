# WORKER_MODE Configuration Guide

## Overview

`WORKER_MODE` tells each Railway service what its role is:

| Service | WORKER_MODE | Purpose |
|---------|-------------|---------|
| **API** | `false` | Accept HTTP requests, queue jobs |
| **Worker** | `true` | Run scrapers, do heavy work |
| **Scheduler** | `false` | Trigger scheduled tasks |

---

## Why This Matters

### Without WORKER_MODE (Confused Services)

```
┌─────────────────────────────────────────┐
│  API Service (WORKER_MODE not set)      │
│                                         │
│  "Should I scrape or just queue?"       │
│  "I don't know what I am!"              │
│                                         │
│  Result: tries to run Playwright        │
│  Result: crashes (no PW installed)      │
└─────────────────────────────────────────┘
```

### With WORKER_MODE (Clear Roles)

```
┌──────────────────────────┐     ┌──────────────────────────┐
│  API Service             │     │  Worker Service          │
│  WORKER_MODE=false       │     │  WORKER_MODE=true        │
│                          │     │                          │
│  "I'm the API gateway"   │     │  "I'm the scraper"       │
│  "I queue jobs to Redis" │     │  "I run Playwright"      │
│                          │     │                          │
│  Action: Queue task ✓    │────►│  Action: Run scrapers ✓  │
└──────────────────────────┘     └──────────────────────────┘
```

---

## Configuration by Service

### 1. API Service

```bash
# Tell service: "You are the API"
WORKER_MODE=false

# Light concurrency (health checks only)
SCRAPER_CONCURRENCY=2

# Required connections
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

**What it does:**
- Accepts HTTP requests from frontend
- Validates input
- Queues scraping jobs to Redis
- Returns task ID immediately
- Polls Redis for results
- **Never runs Playwright**

---

### 2. Worker Service

```bash
# Tell service: "You are the worker"
WORKER_MODE=true

# Heavy concurrency (full scraping)
SCRAPER_CONCURRENCY=4
LIGHT_SCRAPER_CONCURRENCY=4
HEAVY_SCRAPER_CONCURRENCY=2
DOMAIN_COOLDOWN_SECONDS=10

# Required connections
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Playwright (heavy browser automation)
PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# API Keys
SERPAPI_API_KEY=xxx
BRAVE_API_KEY=xxx
```

**What it does:**
- Listens to Redis queue
- Runs scrapers (SerpAPI, Yahoo, Yandex, Brave)
- Runs Playwright scrapers (Facebook, Twitter, Jiji)
- Scores intent
- Saves to database
- **No public port exposed**

---

### 3. Scheduler Service

```bash
# Tell service: "You just trigger tasks"
WORKER_MODE=false

# Only needs Redis
REDIS_URL=${{Redis.REDIS_URL}}
```

**What it does:**
- Runs Celery Beat (cron-like scheduler)
- Triggers agent tasks periodically
- Queues tasks to Redis
- **No scraping, no database**

---

## Code Implementation

### Check WORKER_MODE in Code

```python
# app/core/config.py or similar
import os

WORKER_MODE = os.getenv("WORKER_MODE", "false").lower() == "true"

if WORKER_MODE:
    # This is the worker service
    # Initialize Playwright, heavy scrapers
    from playwright.sync_api import sync_playwright
else:
    # This is API or Scheduler
    # No Playwright, lightweight
    pass
```

### API Endpoint (WORKER_MODE=false)

```python
# app/api/routes/search.py
from app.core.celery_app import celery

@router.post("/search")
async def search(query: str):
    # API queues job, doesn't scrape
    task = celery.send_task('run_scraper_task', args=[query])
    return {"task_id": task.id, "status": "queued"}
```

### Worker Task (WORKER_MODE=true)

```python
# app/core/celery_worker.py
from celery import shared_task

@shared_task
def run_scraper_task(query: str):
    # Worker runs scraping
    # This only runs in Worker service
    from app.services.parallel_scraper_runner import run_scrapers_parallel
    results = run_scrapers_parallel(scrapers, query)
    return results
```

---

## Railway Dashboard Setup

### Step 1: Create Services

```bash
railway add --service api
railway add --service worker
railway add --service scheduler
```

### Step 2: Set Variables per Service

**API Service:**
```bash
railway vars set --service api \
  WORKER_MODE=false \
  SCRAPER_CONCURRENCY=2 \
  DATABASE_URL="${{Postgres.DATABASE_URL}}" \
  REDIS_URL="${{Redis.REDIS_URL}}"
```

**Worker Service:**
```bash
railway vars set --service worker \
  WORKER_MODE=true \
  SCRAPER_CONCURRENCY=4 \
  LIGHT_SCRAPER_CONCURRENCY=4 \
  HEAVY_SCRAPER_CONCURRENCY=2 \
  DOMAIN_COOLDOWN_SECONDS=10 \
  PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
  DATABASE_URL="${{Postgres.DATABASE_URL}}" \
  REDIS_URL="${{Redis.REDIS_URL}}" \
  SERPAPI_API_KEY=xxx
```

**Scheduler Service:**
```bash
railway vars set --service scheduler \
  WORKER_MODE=false \
  REDIS_URL="${{Redis.REDIS_URL}}"
```

### Step 3: Deploy

```bash
railway up
```

---

## Troubleshooting

### Problem: API trying to scrape

**Symptom:** API logs show Playwright errors

**Cause:** `WORKER_MODE` not set or set to `true` in API service

**Fix:**
```bash
railway vars set --service api WORKER_MODE=false
```

### Problem: Worker not processing tasks

**Symptom:** Tasks pile up in Redis, no worker logs

**Cause:** `WORKER_MODE` not set to `true` in Worker service

**Fix:**
```bash
railway vars set --service worker WORKER_MODE=true
```

### Problem: Scheduler crashing

**Symptom:** Scheduler logs show DB connection errors

**Cause:** Scheduler doesn't need DB, but code tries to connect

**Fix:** Ensure code checks `WORKER_MODE` before DB operations in scheduler context

---

## Summary

| Variable | API | Worker | Scheduler |
|----------|-----|--------|-----------|
| `WORKER_MODE` | `false` | `true` | `false` |
| `SCRAPER_CONCURRENCY` | `2` | `4` | N/A |
| `DATABASE_URL` | ✅ | ✅ | ❌ |
| `REDIS_URL` | ✅ | ✅ | ✅ |
| `PLAYWRIGHT_*` | ❌ | ✅ | ❌ |
| `SERPAPI_API_KEY` | ❌ | ✅ | ❌ |

**Remember:**
- `WORKER_MODE=false` = Lightweight, queues jobs
- `WORKER_MODE=true` = Heavy lifting, runs scrapers
