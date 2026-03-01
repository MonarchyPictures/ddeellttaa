# Railway Scaling Strategy — Microservices Architecture

## Why Split API from Scraper?

### The Problem: Scrapers Kill APIs

**Scrapers are resource monsters:**
- **Heavy CPU** - Browser automation maxes CPU cores
- **Heavy memory** - Each Playwright browser uses 500MB+ RAM  
- **Can freeze API** - Blocking requests pile up, timeouts cascade
- **Trigger 429 storms** - Rate limits hit, retries overload system

**Monolith = Death:**
```
┌────────────────────────────────────────┐
│  Container: FastAPI + Playwright       │
│                                        │
│  ┌──────────┐    ┌────────────────┐   │
│  │   API    │    │  Playwright    │   │
│  │  100MB   │    │   1.5GB RAM    │   │
│  │  Fast    │    │   Heavy CPU    │   │
│  └────┬─────┘    └───────┬────────┘   │
│       │                  │            │
│       └────────┬─────────┘            │
│                ▼                       │
│         ┌──────────┐                   │
│         │   💀     │  OOM Killed       │
│         │  CRASH   │  Everything down  │
│         └──────────┘                   │
└────────────────────────────────────────┘
```

### The Solution: Split = Stability

```
┌─────────────────────┐      ┌─────────────────────┐
│   API Service       │      │   Worker Service    │
│   (Lightweight)     │      │   (Heavy lifting)   │
│                     │      │                     │
│  ┌──────────────┐   │      │  ┌──────────────┐   │
│  │   FastAPI    │   │      │  │    Celery    │   │
│  │   100MB RAM  │   │      │  │    Worker    │   │
│  │   Always up  │   │      │  │   2GB RAM    │   │
│  └──────┬───────┘   │      │  └──────┬───────┘   │
│         │           │      │         │           │
│         ▼           │      │         ▼           │
│  ┌──────────────┐   │      │  ┌──────────────┐   │
│  │     Redis    │◄──┼──────┼──┤  Playwright  │   │
│  │     Queue    │   │      │  │   Scrapers   │   │
│  └──────────────┘   │      │  └──────────────┘   │
│                     │      │                     │
│  If worker crashes: │      │  Worker restarts,   │
│  API stays online ✓ │      │  API unaffected ✓   │
└─────────────────────┘      └─────────────────────┘
```

**Split Service Benefits:**
| Aspect | Monolith | Split Services |
|--------|----------|----------------|
| **Memory** | Playwright bloats API | API stays light (~100MB) |
| **CPU** | Scraping blocks requests | API always responsive |
| **Stability** | One crash = all down | Worker crash ≠ API down |
| **Scaling** | Can't scale independently | Workers scale 2x, 3x, etc. |
| **429 Storms** | Kills entire app | Isolated to worker |
| **Deploys** | Full restart | Rolling per service |

---

## 🧱 Recommended Production Setup

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        RAILWAY PROJECT                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │  Service 1   │      │  Service 2   │                    │
│  │   API        │      │   Worker     │                    │
│  │  (FastAPI)   │◄────►│  (Celery)    │                    │
│  │              │      │              │                    │
│  │  • No scrape │      │  • Scrape    │                    │
│  │  • No PW     │      │  • Playwright│                    │
│  │  • Public    │      │  • Score     │                    │
│  │  • Port 8000 │      │  • No port   │                    │
│  └──────────────┘      └──────┬───────┘                    │
│         │                     │                             │
│         │              ┌──────┴───────┐                    │
│         │              │  Service 3   │                    │
│         │              │  Scheduler   │                    │
│         │              │  (Beat)      │                    │
│         │              │              │                    │
│         │              │  • Triggers  │                    │
│         │              │  • Schedule  │                    │
│         │              └──────────────┘                    │
│         │                     │                             │
│         └──────────────┐      │                             │
│                        ▼      ▼                             │
│               ┌──────────────────┐                         │
│               │  Service 4 & 5   │                         │
│               │  Redis + Postgres│                         │
│               │                  │                         │
│               │  • Broker        │                         │
│               │  • Results       │                         │
│               │  • Persistent    │                         │
│               └──────────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Service Breakdown

### Service 1 — API (FastAPI)
**Purpose:** Public-facing REST API only

**Characteristics:**
- Lightweight (no Playwright)
- Exposes port (public URL)
- Handles HTTP requests
- Queues scraping jobs to Redis
- Returns cached/immediate results

**Start Command:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Environment Variables:**
```bash
# Database
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (broker)
REDIS_URL=${{Redis.REDIS_URL}}

# API Keys (for enrichment, not scraping)
SERPAPI_API_KEY=xxx

# No Playwright here!
```

**Resource Limits:**
- RAM: 512MB
- CPU: 1x
- No disk needed

---

### Service 2 — Worker (Celery)
**Purpose:** Heavy scraping and processing

**Characteristics:**
- Has Playwright installed
- Runs scrapers in parallel
- Scores intent
- Saves to DB
- No public port

**Start Command:**
```bash
celery -A app.core.celery_app worker --loglevel=info --concurrency=2 --pool=prefork
```

**Environment Variables:**
```bash
# Same DB and Redis
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Scraper settings
LIGHT_SCRAPER_CONCURRENCY=4
HEAVY_SCRAPER_CONCURRENCY=2
DOMAIN_COOLDOWN_SECONDS=10
PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# API Keys for scraping
SERPAPI_API_KEY=xxx
BRAVE_API_KEY=xxx
```

**Resource Limits:**
- RAM: 2GB (Playwright needs memory)
- CPU: 2x
- Disk: 2GB (Playwright browsers)

**Nixpacks Config:**
```toml
[phases.build]
nixPkgs = ['...', 'playwright-chromium']
```

---

### Service 3 — Scheduler (Celery Beat)
**Purpose:** Trigger scheduled agents

**Characteristics:**
- Lightweight
- Runs cron-like scheduler
- Queues agent tasks to Redis
- No scraping here

**Start Command:**
```bash
celery -A app.core.celery_app beat --loglevel=info
```

**Environment Variables:**
```bash
REDIS_URL=${{Redis.REDIS_URL}}
# No DB needed (only queues tasks)
```

**Resource Limits:**
- RAM: 256MB
- CPU: 0.5x

---

### Service 4 — Redis
**Purpose:** Celery broker and result backend

**Railway Add-on:** Redis

**Use Case:**
- Task queue (API → Worker)
- Results backend
- Rate limiting cache

---

### Service 5 — Postgres
**Purpose:** Persistent data storage

**Railway Add-on:** PostgreSQL

**Tables:**
- `leads` - Scraped leads
- `agents` - Agent schedules
- `agent_schedules` - Run history

---

## Implementation Steps

### Step 1: Create Railway Project

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create project
railway init
```

### Step 2: Add Services

```bash
# Service 1: API
railway add --service api

# Service 2: Worker  
railway add --service worker

# Service 3: Scheduler
railway add --service scheduler

# Addons
railway add --database postgres
railway add --redis redis
```

### Step 3: Configure Services

**API Service:**
```bash
railway vars set --service api \
  START_COMMAND="uvicorn app.main:app --host 0.0.0.0 --port $PORT" \
  DATABASE_URL="${{Postgres.DATABASE_URL}}" \
  REDIS_URL="${{Redis.REDIS_URL}}"
```

**Worker Service:**
```bash
railway vars set --service worker \
  START_COMMAND="celery -A app.core.celery_app worker --loglevel=info --concurrency=2" \
  DATABASE_URL="${{Postgres.DATABASE_URL}}" \
  REDIS_URL="${{Redis.REDIS_URL}}" \
  PLAYWRIGHT_BROWSERS_PATH="/ms-playwright"
```

### Step 4: Deploy

```bash
# Deploy all services
railway up

# Check logs
railway logs --service api
railway logs --service worker
railway logs --service scheduler
```

---

## Code Changes Required

### 1. Separate Scraping from API

**Current (Bad):**
```python
# app/api/routes/core.py
@router.post("/search")
async def search():
    # API does scraping directly ❌
    results = await run_scrapers_parallel(...)
    return results
```

**New (Good):**
```python
# app/api/routes/core.py
@router.post("/search")
async def search():
    # API queues job, returns task ID
    task = celery.send_task('run_scraper_task', args=[query])
    return {"task_id": task.id, "status": "queued"}

# Client polls for results
@router.get("/search/{task_id}")
async def get_search_results(task_id: str):
    result = AsyncResult(task_id)
    return {"status": result.status, "results": result.result}
```

### 2. Celery Task for Scraping

```python
# app/core/celery_worker.py

@celery_app.task(bind=True, max_retries=3)
def run_scraper_task(self, query: str, location: str = "Kenya"):
    """Worker task - runs scraping."""
    try:
        # This runs in Worker service (has Playwright)
        from app.services.kenya_high_recall_pipeline import generate_high_recall_queries
        from app.services.parallel_scraper_runner import run_scrapers_parallel
        
        queries = generate_high_recall_queries(query, location)
        
        all_results = []
        for q in queries:
            results = run_scrapers_parallel(scrapers, q, location)
            all_results.extend(results)
        
        # Score and save
        leads = process_high_recall_results(all_results)
        save_leads_to_db(leads, query)
        
        return {"leads": leads, "count": len(leads)}
    
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
```

### 3. Update Celery Config

```python
# app/core/celery_app.py
from celery import Celery

celery_app = Celery(
    "delta9",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL"),
    include=["app.core.celery_worker"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 min max per task
    worker_prefetch_multiplier=1,  # Don't prefetch
)
```

---

## Environment Variables by Service

### API Service Environment
```bash
# Mode
detect_horizontal
WORKER_MODE=false

# Concurrency (light - only for health checks)
SCRAPER_CONCURRENCY=2

# Database & Redis
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Feature flags
HIGH_RECALL_MODE=true

# No Playwright APIs needed here
```

### Worker Service Environment
```bash
# Mode
WORKER_MODE=true

# Concurrency (heavy scraping)
SCRAPER_CONCURRENCY=4
LIGHT_SCRAPER_CONCURRENCY=4
HEAVY_SCRAPER_CONCURRENCY=2
DOMAIN_COOLDOWN_SECONDS=10

# Database & Redis
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# API Keys for scraping
SERPAPI_API_KEY=xxx
BRAVE_API_KEY=xxx

# Playwright (required for heavy scrapers)
PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Feature flags
HIGH_RECALL_MODE=true
```

### Scheduler Service Environment
```bash
# Mode
WORKER_MODE=false

# Only needs Redis to queue tasks
REDIS_URL=${{Redis.REDIS_URL}}

# Feature flags
HIGH_RECALL_MODE=true
```

### Quick Reference Table

| Variable | API | Worker | Scheduler | Description |
|----------|-----|--------|-----------|-------------|
| `WORKER_MODE` | `false` | `true` | `false` | Service type identifier |
| `SCRAPER_CONCURRENCY` | `2` | `4` | N/A | Scraping parallelism |
| `DATABASE_URL` | ✅ | ✅ | ❌ | Postgres connection |
| `REDIS_URL` | ✅ | ✅ | ✅ | Redis broker |
| `SERPAPI_API_KEY` | ❌ | ✅ | ❌ | Scraper API key |
| `BRAVE_API_KEY` | ❌ | ✅ | ❌ | Scraper API key |
| `PLAYWRIGHT_*` | ❌ | ✅ | ❌ | Browser paths |
| `HIGH_RECALL_MODE` | ✅ | ✅ | ✅ | Feature flag |

---

## Monitoring

### Health Checks

**API Health:**
```bash
GET /api/health
# Should return immediately (no DB query)
```

**Worker Health:**
```bash
# Celery built-in ping
celery -A app.core.celery_app inspect ping
```

**Queue Depth:**
```bash
# Check Redis queue length
redis-cli LLEN celery
```

### Logs

```bash
# All services
railway logs

# Specific service
railway logs --service worker

# Follow
railway logs --service worker --follow
```

---

## Auto-Scaling Strategy

### Rule: Scale Workers First, Not API

**When leads volume increases:**

```
Before Scaling:
┌──────────┐     ┌──────────────────┐
│   API    │────►│  1 Worker        │
│  (OK)    │     │  (Overloaded)    │
└──────────┘     └──────────────────┘
                          │
                   Queue backing up

After Scaling (Correct):
┌──────────┐     ┌──────────────────┐
│   API    │────►│  3 Workers       │
│  (OK)    │     │  (Load balanced) │
└──────────┘     └──────────────────┘
                          │
                   Queue processing fast
```

**Why scale workers only?**
- API is lightweight (just queues jobs)
- Scraping is the bottleneck
- More workers = more parallel scraping
- API only needs scaling if HTTP requests > 1000/min

**Railway Scale Command:**
```bash
# Scale workers horizontally
railway scale --service worker --replicas 3

# Check queue depth first
redis-cli LLEN celery

# Scale based on queue
tasks_pending=$(redis-cli LLEN celery)
if [ $tasks_pending -gt 50 ]; then
    railway scale --service worker --replicas 5
fi
```

**Scaling Limits:**
- Start: 1 worker (2GB RAM each)
- Scale to: 3-5 workers max
- Don't exceed: 20 total concurrent scrapers across all workers

---

## Rate Limiting Per Worker

### Global Request Limit: 30/minute per worker

**Why?** Prevents 429 explosion when scaling.

```python
# app/services/rate_limiter.py
import time
from functools import wraps

class WorkerRateLimiter:
    """
    Per-worker rate limiter.
    GLOBAL_REQUEST_LIMIT = 30 per minute per worker.
    """
    REQUESTS_PER_MINUTE = 30
    
    def __init__(self):
        self.requests = []
    
    def can_request(self) -> bool:
        """Check if worker can make another request."""
        now = time.time()
        # Remove requests older than 60 seconds
        self.requests = [r for r in self.requests if now - r < 60]
        # Check limit
        return len(self.requests) < self.REQUESTS_PER_MINUTE
    
    def record_request(self):
        """Record that worker made a request."""
        self.requests.append(time.time())
    
    def wait_time(self) -> float:
        """Get seconds to wait before next request allowed."""
        if self.can_request():
            return 0
        now = time.time()
        oldest = min(self.requests)
        return 60 - (now - oldest)

# Global limiter instance
worker_limiter = WorkerRateLimiter()


def rate_limited(func):
    """Decorator to rate limit function calls."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Wait if rate limited
        while not worker_limiter.can_request():
            wait = worker_limiter.wait_time()
            await asyncio.sleep(wait)
        
        # Record and execute
        worker_limiter.record_request()
        return await func(*args, **kwargs)
    return wrapper
```

### Usage in Scrapers

```python
# In each scraper's search method
from app.services.rate_limiter import rate_limited

class YahooScraper:
    @rate_limited
    async def search(self, query, location):
        # This call is now rate limited to 30/min per worker
        return await self._do_search(query, location)
```

### Environment Variable

```bash
# Per-worker rate limit
GLOBAL_REQUEST_LIMIT=30  # requests per minute per worker
```

### Scaling + Rate Limiting Math

| Workers | Requests/Min Total | Safe? |
|---------|-------------------|-------|
| 1 | 30 | ✅ Yes |
| 2 | 60 | ✅ Yes |
| 3 | 90 | ✅ Yes |
| 5 | 150 | ⚠️ Monitor |
| 10 | 300 | ❌ Risk 429 |

**Rule:** Scale workers, but monitor domain cooldown and 429 rates.

---

## Troubleshooting

### Worker Memory Issues

**Symptom:** Worker killed (OOM)

**Fix:**
```bash
# Reduce concurrency
railway vars set --service worker CELERY_CONCURRENCY=1

# Add swap
railway vars set --service worker SWAP=1GB
```

### Queue Backup

**Symptom:** Tasks pile up in Redis

**Fix:**
```bash
# Scale workers horizontally
railway scale --service worker --replicas 2
```

### API Slow Response

**Symptom:** API timeouts

**Fix:**
```bash
# API should never scrape - verify task queue is used
# Check worker is processing tasks
railway logs --service worker
```

---

## Cost Estimation (Railway)

| Service | Tier | Monthly Cost |
|---------|------|--------------|
| API | 512MB RAM | ~$5 |
| Worker | 2GB RAM | ~$20 |
| Scheduler | 256MB RAM | ~$3 |
| Redis | 256MB | ~$3 |
| Postgres | 1GB | ~$10 |
| **Total** | | **~$41/mo** |

---

## Summary

| Before (Monolith) | After (Microservices) |
|-------------------|----------------------|
| Single container crashes | 3 services scale independently |
| Playwright bloats API | API lightweight, Worker heavy |
| Scraping blocks requests | Async queue processing |
| Hard to debug | Clear service boundaries |
| Memory crashes | Resource isolation |

**Deploy this way for production stability.**
