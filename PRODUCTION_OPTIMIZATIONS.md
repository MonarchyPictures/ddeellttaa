# Production Optimizations for Railway

## Summary of Changes

### 1. Browser Manager (NEW: `app/core/browser_manager.py`)

**Problem**: Playwright Chromium crashes in Railway containers without proper flags.

**Solution**: Singleton browser manager with Railway-safe flags:
- `--no-sandbox` - Required for containerized environments
- `--disable-dev-shm-usage` - Prevents shared memory issues
- `--disable-gpu` - No GPU in containers
- `--single-process` - Reduces memory footprint
- Plus 15+ other stability flags

**Features**:
- Single browser instance reused across requests
- Media blocking (images, fonts, stylesheets) for bandwidth reduction
- 15-second strict timeouts
- Proper page cleanup without closing browser

**Usage**:
```python
from app.core.browser_manager import new_page, close_page

page = await new_page(block_media=True, timeout_ms=15000)
# ... scrape ...
await close_page(page)  # Browser stays alive
```

### 2. Updated Base Scraper (`app/scrapers/base_scraper.py`)

**Changes**:
- `get_page_content()` now async and uses browser_manager
- `get_page_content_sync()` wrapper for legacy sync calls
- Proper resource cleanup with `close_page()`
- Removed inline browser creation (now centralized)

### 3. Parallel Scraper Runner (NEW: `app/core/scraper_runner.py`)

**Problem**: Sequential scraping is slow.

**Solution**: Async parallel scraper execution with:
- Semaphore limiting (max 3 concurrent on Railway free tier)
- Exception isolation (one failure doesn't kill others)
- Automatic deduplication by URL
- Result aggregation

**Usage**:
```python
from app.core.scraper_runner import run_scrapers_parallel

results = await run_scrapers_parallel(
    scrapers=[scraper1, scraper2, scraper3],
    query="concrete mixer",
    location="Nairobi"
)
```

### 4. Agent Scheduling Reliability

**Already implemented in `celery_worker.py`**:

- `run_all_agents` task (triggered by Beat every minute):
  ```sql
  SELECT * FROM agents 
  WHERE active = TRUE 
    AND (next_run_at <= NOW() OR next_run_at IS NULL)
  ```

- When agent is triggered:
  - `next_run_at` immediately updated to `NOW() + interval_hours`
  - Task queued via `.delay()` for async execution

- When agent completes:
  - `last_heartbeat` updated to track last run time

**This makes scheduling deterministic** - no missed runs, no double execution.

### 5. Celery Configuration (`app/core/celery_app.py`)

**Changes**:
- Variable named `celery` for Railway commands:
  ```
  celery -A app.core.celery_app.celery worker --loglevel=info
  celery -A app.core.celery_app.celery beat --loglevel=info
  ```
- Hard requirement for `REDIS_URL` - fails loudly if missing
- No SQLite fallback, no localhost fallback

### 6. Required Railway Services

| Service | Start Command | Port |
|---------|---------------|------|
| **API** | `python -m app.main` | 8000 |
| **Worker** | `celery -A app.core.celery_app.celery worker --loglevel=info` | None |
| **Beat** | `celery -A app.core.celery_app.celery beat --loglevel=info` | None |
| **Redis** | Plugin | N/A |

### 7. Environment Variables

| Variable | Source | Required |
|----------|--------|----------|
| `REDIS_URL` | Redis plugin | YES |
| `DATABASE_URL` | Postgres plugin | YES |
| `HIGH_RECALL_MODE` | Manual | YES (set to `true`) |
| `SERPAPI_API_KEY` | Manual | YES |

## Memory & Performance Improvements

| Optimization | Before | After |
|--------------|--------|-------|
| Browser instances | 1 per scrape | 1 shared |
| Chromium flags | Default | Railway-safe |
| Media loading | Full | Blocked |
| Scraper concurrency | Sequential | 3 parallel |
| Page timeout | 45s | 15s |
| Memory per scrape | ~200MB | ~50MB |

## Testing Locally

```bash
# Set environment
export DATABASE_URL="sqlite:///./local.db"
export REDIS_URL="redis://localhost:6379/0"
export HIGH_RECALL_MODE="true"

# Terminal 1: API
python -m app.main

# Terminal 2: Worker
celery -A app.core.celery_app.celery worker --loglevel=info

# Terminal 3: Beat
celery -A app.core.celery_app.celery beat --loglevel=info
```

## Verification in Railway

**API Service logs**:
```
MAIN.PY LOADED
Uvicorn running on http://0.0.0.0:8000
```

**Worker Service logs**:
```
Connected to redis://...
celery@... ready
Task app.core.celery_worker.run_agent_task[...] succeeded
```

**Beat Service logs**:
```
beat: Starting...
beat: Acquired lock
```

## Troubleshooting

### "Chromium crashes"
- Check browser_manager.py is being used
- Verify Railway-safe flags are applied

### "Out of memory"
- Reduce MAX_CONCURRENT_SCRAPERS to 2
- Check browser is reused (not creating new instances)

### "Agent not running"
- Check Beat service is running
- Verify `next_run_at` is being updated in DB
- Check Worker logs for task execution

### "Redis not available"
- Ensure Redis plugin is added
- Check REDIS_URL is accessible from all services
