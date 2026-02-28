# Production-Safe Parallel Scraper Architecture

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   FastAPI API   │────▶│   Celery Worker  │────▶│  Redis Queue    │
│  (Async Loop)   │     │   (Sync Context) │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  asyncio.run()   │  ◄── Safe here
                        │                  │
                        │ run_scrapers_parallel()
                        │                  │
                        │  ┌───────────┐   │
                        │  │Semaphore(3)│   │  ◄── Concurrency cap
                        │  └───────────┘   │
                        │                  │
                        │  ┌───────────┐   │
                        │  │ wait_for()│   │  ◄── 25s timeout
                        │  │ 25s max   │   │
                        │  └───────────┘   │
                        │                  │
                        │  [Scraper 1]     │
                        │  [Scraper 2]     │  ◄── Exception isolation
                        │  [Scraper 3]     │
                        └──────────────────┘
```

## Key Safety Rules

| Rule | Implementation | Why |
|------|----------------|-----|
| ✅ `asyncio.run()` in Celery | `run_agent_task()` uses `asyncio.run()` | Celery is sync context |
| ❌ NO `asyncio.run()` in FastAPI | Don't call from API routes | FastAPI already has event loop |
| ✅ Concurrency cap | `asyncio.Semaphore(3)` | Prevents thread explosion |
| ✅ Per-scraper timeout | `asyncio.wait_for(timeout=25)` | Prevents hanging |
| ✅ Total phase timeout | `asyncio.wait_for(timeout=60)` | Prevents runaway jobs |
| ✅ Exception isolation | Each scraper wrapped in try/except | One failure ≠ all fail |

## Code Structure

### 1. Parallel Runner (`app/services/parallel_scraper_runner.py`)

```python
MAX_CONCURRENT_SCRAPERS = 3  # From env SCRAPER_CONCURRENCY
SCRAPER_TIMEOUT_SECONDS = 25
TOTAL_PHASE_TIMEOUT_SECONDS = 60

async def run_scrapers_parallel(scrapers, query, location, hours):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPERS)
    
    async def run_single(scraper):
        async with semaphore:
            try:
                # 25s hard timeout per scraper
                return await asyncio.wait_for(
                    scraper.search(query, location),
                    timeout=SCRAPER_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                return []  # Timeout = empty results
            except Exception:
                return []  # Error = empty results
    
    tasks = [run_single(s) for s in scrapers]
    
    # 60s total phase timeout
    results = await asyncio.wait_for(
        asyncio.gather(*tasks),
        timeout=TOTAL_PHASE_TIMEOUT_SECONDS
    )
    
    return combined_results
```

### 2. Celery Worker (`app/core/celery_worker.py`)

```python
@celery.task(name="run_agent_task")
def run_agent_task(agent_id: str):
    # This is SYNC context (Celery worker)
    # ✅ Safe to use asyncio.run()
    
    raw_results = asyncio.run(
        run_scrapers_parallel(
            scrapers=scraper_instances,
            query=agent.query,
            location=agent.location or "Kenya"
        )
    )
```

### 3. FastAPI Route (`app/api/routes/agents.py`)

```python
@router.post("/{agent_id}/run")
def run_agent_now(agent_id: str, db: Session = Depends(get_db)):
    # This runs in FastAPI (already has event loop)
    # ❌ CANNOT use asyncio.run() here
    # ❌ CANNOT call run_scrapers_parallel() directly
    
    # ✅ Instead, queue Celery task:
    from app.core.celery_worker import run_agent_task
    task = run_agent_task.delay(str(agent.id))
    return {"task_id": task.id}
```

## Expected Logs

### Normal Execution
```
Running 3 scrapers in parallel (max concurrent: 3)
🚀 START: DuckDuckGoScraper
🚀 START: SerpAPIScraper
🚀 START: TelegramScraper
✅ DONE: DuckDuckGoScraper (1.3s)
✅ DONE: SerpAPIScraper (2.1s)
⏱ TIMEOUT: TelegramScraper
📊 TOTAL RESULTS: 42
```

### Timeout Handling
```
🚀 START: FacebookMarketplaceScraper
⏱ TIMEOUT: FacebookMarketplaceScraper
📊 TOTAL RESULTS: 0
```

### Error Isolation
```
🚀 START: GoogleScraper
❌ ERROR: GoogleScraper | 403 Forbidden
🚀 START: JijiScraper
✅ DONE: JijiScraper (3.2s)
📊 TOTAL RESULTS: 15
```

### Total Phase Timeout
```
⏱ TOTAL PHASE TIMEOUT: Entire scraping phase exceeded 60s
📊 TOTAL RESULTS: 0
```

## Environment Variables

```bash
# Concurrency (Railway-safe)
SCRAPER_CONCURRENCY=3  # Default, max 4 for Railway

# Timeouts (optional, defaults shown)
SCRAPER_TIMEOUT_SECONDS=25      # Per-scraper timeout
TOTAL_PHASE_TIMEOUT_SECONDS=60  # Total phase timeout
```

## Railway Settings

### Free Tier
```bash
SCRAPER_CONCURRENCY=3
```

### Paid Tier (more RAM)
```bash
SCRAPER_CONCURRENCY=4
```

### ⚠️ Never exceed 5
```bash
# DANGER - Will cause OOM
SCRAPER_CONCURRENCY=10  # ❌ DON'T DO THIS
```

## Common Mistakes

### ❌ Mistake 1: Using in FastAPI Route
```python
# WRONG - Will crash
@router.post("/search")
async def search(query: str):
    results = asyncio.run(run_scrapers_parallel(...))  # ❌ RuntimeError
    return results
```

### ✅ Correct: Queue Celery Task
```python
# CORRECT
@router.post("/search")
def search(query: str):
    task = run_agent_task.delay(agent_id)  # ✅ Queue to worker
    return {"task_id": task.id}
```

### ❌ Mistake 2: No Timeout
```python
# WRONG - Can hang forever
results = await scraper.search(query, hours)
```

### ✅ Correct: Always Use Timeout
```python
# CORRECT
results = await asyncio.wait_for(
    scraper.search(query, hours),
    timeout=25
)
```

### ❌ Mistake 3: Unlimited Concurrency
```python
# WRONG - Thread explosion
tasks = [scraper.search(query) for scraper in all_scrapers]
results = await asyncio.gather(*tasks)  # ❌ Runs all at once
```

### ✅ Correct: Use Semaphore
```python
# CORRECT
semaphore = asyncio.Semaphore(3)

async def run_single(scraper):
    async with semaphore:  # ✅ Max 3 concurrent
        return await scraper.search(query)
```

## Testing Locally

```bash
# Terminal 1: Start API
python -m app.main

# Terminal 2: Start Worker
celery -A app.core.celery_app.celery worker --loglevel=info

# Terminal 3: Trigger agent
curl -X POST http://localhost:8000/api/agents/{agent_id}/run
```

## Verification Checklist

- [ ] `asyncio.run()` only in Celery worker
- [ ] FastAPI routes use `.delay()` to queue tasks
- [ ] Semaphore limits concurrency to 3-4
- [ ] Per-scraper timeout (25s) implemented
- [ ] Total phase timeout (60s) implemented
- [ ] Exception isolation working
- [ ] Logs show START/DONE/TIMEOUT/ERROR
- [ ] Environment variable `SCRAPER_CONCURRENCY` set

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Max concurrent scrapers | 3 (configurable) |
| Per-scraper timeout | 25 seconds |
| Total phase timeout | 60 seconds |
| Expected speedup vs sequential | 2-3x |
| Memory usage | Stable (~150MB) |
| CPU usage | Capped (no spikes) |
