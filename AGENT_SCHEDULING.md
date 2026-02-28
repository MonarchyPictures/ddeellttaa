# Agent Scheduling System - Production Ready

## Overview

Deterministic DB-based scheduling that eliminates:
- Duplicate runs
- Missed runs
- "Last Run: Never" issues
- Sync fallback reliance

**Core Principle**: Database is the SINGLE SOURCE OF TRUTH for scheduling.

## How It Works

### 1. Beat Service (Trigger Only)

Runs every minute:
```python
@celery.task(name="run_all_agents")
def run_all_agents():
    # 1. Deactivate expired agents
    # 2. Query DB: SELECT * FROM agents 
    #              WHERE active = TRUE 
    #                AND is_running = FALSE
    #                AND next_run_at <= NOW()
    # 3. For each agent:
    #    - Mark is_running = TRUE (prevents duplicates)
    #    - Queue run_agent_task.delay(agent_id)
```

**Key**: Beat only SCANS. DB decides execution.

### 2. Agent Execution Flow

```
run_agent_task(agent_id)
  ↓
Check agent exists & should_execute_agent()
  ↓
Get scrapers from registry
  ↓
Run scrapers in parallel (max 3 concurrent)
  ↓
complete_agent_execution()
  ↓
Update: last_run = NOW
       next_run = NOW + interval_hours
       is_running = FALSE
```

### 3. Race Condition Protection

```python
def mark_agent_running(db, agent):
    # Re-query with lock:
    fresh_agent = db.query(Agent).filter(
        Agent.id == agent.id,
        Agent.is_running == FALSE  # Only if not already running
    ).first()
    
    if not fresh_agent:
        return False  # Another worker got it
    
    fresh_agent.is_running = TRUE
    db.commit()
    return True
```

## Database Schema

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    query VARCHAR NOT NULL,
    interval_hours INTEGER DEFAULT 2,
    
    -- Scheduling fields
    next_run_at TIMESTAMP NOT NULL,    -- When to run next
    last_heartbeat TIMESTAMP,          -- Last run time
    is_running BOOLEAN DEFAULT FALSE,  -- Currently executing?
    active BOOLEAN DEFAULT TRUE,       -- Enabled?
    
    -- Lifecycle
    start_time TIMESTAMP,
    end_time TIMESTAMP,                -- Expiration
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast scheduling queries
CREATE INDEX idx_agents_schedule ON agents(active, is_running, next_run_at);
```

## API Endpoints

### Create Agent
```http
POST /api/agents/
{
    "name": "Concrete Mixer Buyers",
    "query": "concrete mixer",
    "location": "Nairobi",
    "interval_hours": 2,
    "duration_days": 7
}
```

Response includes:
```json
{
    "id": "...",
    "execution_status": {
        "status": "due",
        "is_active": true,
        "is_running": false,
        "last_run": null,
        "next_run": "2026-02-27T20:00:00",
        "time_until_next": "0h 0m",
        "interval_hours": 2
    }
}
```

### Get Agent Status
```http
GET /api/agents/{agent_id}
```

Returns real-time execution status.

### Trigger Agent Now
```http
POST /api/agents/{agent_id}/run
```

Manually queues agent for execution.

## Scheduling Scenarios

### Scenario 1: Normal Execution

1. Agent created with `next_run_at = NOW()`
2. Beat scans at :00 → Finds agent due
3. `mark_agent_running()` → Sets `is_running = TRUE`
4. Queues `run_agent_task`
5. Worker executes scrapers
6. `complete_agent_execution()` → Sets `next_run_at = NOW + 2h`, `is_running = FALSE`
7. Next run in 2 hours

### Scenario 2: Worker Crash

1. Worker starts agent, sets `is_running = TRUE`
2. Worker crashes mid-execution
3. `is_running` stays `TRUE` in DB
4. Beat scans → Agent skipped (is_running = TRUE)
5. **Future improvement**: Timeout detection

### Scenario 3: Duplicate Beat Trigger

1. Beat 1 scans → Finds agent due
2. Beat 1 calls `mark_agent_running()` → Success
3. Beat 2 scans → Same agent
4. Beat 2 calls `mark_agent_running()` → Fails (is_running already TRUE)
5. Only one task queued

### Scenario 4: Agent Expiration

1. Agent reaches `end_time`
2. Beat scans → `deactivate_expired_agents()` sets `active = FALSE`
3. Agent never runs again

## Parallel Scraping

Controlled concurrency prevents resource exhaustion:

```python
MAX_CONCURRENT_SCRAPERS = 3

async def run_scrapers_parallel(scrapers, query, location):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPERS)
    
    async def run_one(scraper):
        async with semaphore:  # Only 3 run at once
            return await scraper.search(query, location)
    
    tasks = [run_one(s) for s in scrapers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions, combine results
    return combined_results
```

## Monitoring

### Check Agent Status
```bash
# Get all agents with status
curl /api/agents/

# Response shows:
# - status: "running" | "scheduled" | "due" | "inactive"
# - is_running: true/false
# - time_until_next: "2h 30m"
```

### Worker Logs
```
Found 3 agents due for execution
Triggering agent 'Concrete Mixer' (ID: ...)
Agent ...: Running 3 scrapers in parallel
Agent ...: Scraping complete. 15 total results
Agent ... completed successfully. Next run at ...
```

## Troubleshooting

### "Agent not running"
1. Check Beat service is running
2. Check `next_run_at` is in the past
3. Check `is_running` is not stuck TRUE

### "Duplicate runs"
1. Check `mark_agent_running()` is working
2. Verify DB transaction isolation

### "Last Run: Never"
1. Check Worker service is running
2. Check `run_agent_task` is not failing
3. Verify Redis connection

## Railway Configuration

### Services
| Service | Command |
|---------|---------|
| API | `python -m app.main` |
| Worker | `celery -A app.core.celery_app.celery worker --loglevel=info` |
| Beat | `celery -A app.core.celery_app.celery beat --loglevel=info` |

### Beat Schedule (celery_app.py)
```python
beat_schedule={
    "check-agents-every-minute": {
        "task": "app.core.celery_worker.run_all_agents",
        "schedule": 60.0,  # Every 60 seconds
    },
}
```

## Safety Rules

✅ DO:
- Let DB control scheduling
- Use `is_running` flag
- Handle exceptions gracefully
- Run max 3 scrapers in parallel

❌ DON'T:
- Use in-memory timing
- Run 10+ scrapers concurrently
- Ignore `is_running` flag
- Block API thread
