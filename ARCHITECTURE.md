# DELTA-9 PRODUCTION ARCHITECTURE
## Hardened Lead Intelligence Platform

---

## System Overview

Delta-9 is a **production-grade, self-healing lead intelligence platform** designed for the Kenyan market. It discovers real buyer leads from live sources with strict validation to ensure data integrity.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DELTA-9 ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   Telegram   │    │    Jiji      │    │   Reddit     │    │  Facebook │ │
│  │   Scraper    │    │   Scraper    │    │   Scraper    │    │  Scraper  │ │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └─────┬─────┘ │
│         │                   │                   │                   │       │
│         └───────────────────┴───────────────────┴───────────────────┘       │
│                                     │                                       │
│                              ┌──────┴──────┐                                │
│                              │   RawLead   │                                │
│                              └──────┬──────┘                                │
│                                     │                                       │
│                    ┌────────────────┼────────────────┐                      │
│                    │                │                │                      │
│              ┌─────┴─────┐    ┌─────┴─────┐    ┌────┴────┐                 │
│              │ Heartbeat │    │   Rate    │    │  Error  │                 │
│              │  Monitor  │    │  Limiter  │    │ Handler │                 │
│              └───────────┘    └───────────┘    └─────────┘                 │
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║                    HARDENED LEAD PIPELINE                             ║ │
│  ║  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         ║ │
│  ║  │ SCRAPE  │→│  CLEAN  │→│ INTENT  │→│ EXTRACT │→│ VERIFY  │         ║ │
│  ║  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘         ║ │
│  ║       │                                                            │  ║ │
│  ║  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         ║ │
│  ║  │ SOURCE  │→│FRESHNESS│→│  SCORE  │→│ DEDUPE  │→│  STORE  │         ║ │
│  ║  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘         ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                    │                                        │
│                           ┌────────┴────────┐                               │
│                           │  LeadSchema     │                               │
│                           │  (Validated)    │                               │
│                           └────────┬────────┘                               │
│                                    │                                        │
│                    ┌───────────────┼───────────────┐                        │
│                    │               │               │                        │
│              ┌─────┴────┐    ┌─────┴────┐    ┌────┴────┐                   │
│              │PostgreSQL│    │  Redis   │    │  Logs   │                   │
│              └──────────┘    └──────────┘    └─────────┘                   │
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║                    SYSTEM GUARDIAN (Self-Healing)                     ║ │
│  ║                                                                       ║ │
│  ║  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐   ║ │
│  ║  │   Health    │  │   Failure   │  │   Auto      │  │   Alert    │   ║ │
│  ║  │   Checks    │→ │   Detect    │→ │   Recover   │→ │   Notify   │   ║ │
│  ║  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘   ║ │
│  ║                                                                       ║ │
│  ║  Every 60 seconds:                                                    ║ │
│  ║  • Check scraper heartbeats                                           ║ │
│  ║  • Check database connectivity                                        ║ │
│  ║  • Check pipeline queue                                               ║ │
│  ║  • Check system resources                                             ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                                                             │
│                           ┌─────────────┐                                   │
│                           │  React UI   │                                   │
│                           │  Frontend   │                                   │
│                           └─────────────┘                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Principles

### 1. **NEVER Generate Fake Data**
- ❌ No AI-generated leads
- ❌ No fabricated phone numbers
- ❌ No invented buyer text
- ✅ Every lead from real source post

### 2. **Strict Validation**
Every lead MUST have:
- `query` - What was searched
- `text` - Original post text
- `phone` - Verified Kenya phone
- `source_platform` - Where it came from
- `source_name` - Group/page name
- `source_url` - Link to original
- `timestamp` - When posted
- `location` - City/region
- `intent_score` - 0-100

### 3. **Self-Healing**
- Automatic scraper restart on failure
- Pipeline queue flushing when stuck
- Health monitoring every 60 seconds
- Zero manual intervention required

---

## Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────┐
│                     LEAD PIPELINE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. SCRAPE    → Validate input has required fields              │
│                 REJECT if missing any field                     │
│                                                                 │
│  2. CLEAN     → Normalize text, remove whitespace               │
│                 Sanitize input                                  │
│                                                                 │
│  3. INTENT    → Detect buyer keywords                           │
│                 looking for, need, natafuta, etc.               │
│                 REJECT if seller keywords found                 │
│                                                                 │
│  4. EXTRACT   → Extract phone number from text                  │
│                 REJECT if no phone found                        │
│                                                                 │
│  5. VERIFY    → Validate Kenya phone format                     │
│                 ^(\+254|0)[17]\d{8}$                            │
│                 REJECT if invalid                               │
│                                                                 │
│  6. SOURCE    → Verify source attribution                       │
│                 Validate platform matches URL                   │
│                 REJECT if source invalid                        │
│                                                                 │
│  7. FRESHNESS → Check timestamp                                 │
│                 HOT   = < 24h                                   │
│                 WARM  = < 3 days                                │
│                 COLD  = < 7 days                                │
│                 DISCARD if > 7 days                             │
│                                                                 │
│  8. SCORE     → Calculate intent score 0-100                    │
│                 < 40 = DISCARD                                  │
│                                                                 │
│  9. DEDUPE    → Check for duplicates                            │
│                 hash(phone + text + date)                       │
│                 REJECT if duplicate                             │
│                                                                 │
│  10. STORE    → Save to PostgreSQL                              │
│                 Return validated LeadSchema                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Guardian

The System Guardian monitors all components and auto-recovers from failures.

### Health Checks (Every 60s)

```python
checks = [
    scraper_heartbeats(),      # Check last heartbeat < 2 min
    database_connectivity(),   # PostgreSQL ping
    pipeline_queue(),          # Queue size < 10,000
    system_resources(),        # CPU < 85%, RAM < 90%
    api_health(),             # API responsiveness
]
```

### Auto-Recovery Actions

| Failure Type | Action | Description |
|--------------|--------|-------------|
| Scraper dead | Restart | Kill and restart scraper process |
| Queue stuck | Flush | Clear backlog and restart |
| Memory high | Clear cache | Flush Redis/memory cache |
| DB down | Alert | Send critical alert |
| Critical error | Alert | Page on-call engineer |

---

## Buyer Intent Detection

### Accepted Keywords (Buyer Intent)
```
English:
- looking for
- need
- want
- searching for
- anyone selling
- where can i buy
- who has
- urgently
- budget ready
- cash on hand

Swahili:
- natafuta
- niko natafuta
- nahtaji
- ninahitaji
- tafuta
```

### Rejected Keywords (Seller Intent)
```
- selling
- available
- for sale
- price
- discount
- offer
- call me
- dm me
- contact me
- inbox
- stock
- supply
- wholesale
- retail
- shop
- store
```

---

## Phone Verification

### Kenya Phone Format
```regex
^(\+254|0)[17]\d{8}$
```

### Valid Examples
- ✅ `+254712345678`
- ✅ `0712345678`
- ✅ `0112345678`

### Invalid Examples
- ❌ `+255712345678` (Tanzania)
- ❌ `071234567` (too short)
- ❌ `07123456789` (too long)
- ❌ `+1234567890` (wrong country)

---

## Lead Freshness

| Classification | Age | Priority |
|----------------|-----|----------|
| 🔥 HOT | < 24 hours | Highest |
| 🟡 WARM | < 3 days | Medium |
| ❄️ COLD | < 7 days | Low |
| 🗑️ STALE | > 7 days | DISCARD |

---

## Deduplication

Uses 3-layer deduplication:

1. **Exact Hash** - `hash(phone + text[:100] + date)`
2. **Phone + Time** - Same phone within 24 hours
3. **Text Similarity** - 85%+ similar text

---

## API Endpoints

### Guardian API
```
GET  /api/guardian/health          → System health status
GET  /api/guardian/scrapers        → Scraper statuses
POST /api/guardian/scrapers/{id}/restart → Restart scraper
GET  /api/guardian/pipeline/stats  → Pipeline statistics
GET  /api/guardian/errors          → Recent errors
POST /api/guardian/cache/clear     → Clear caches
GET  /api/guardian/logs/search?q=  → Search logs
```

### Leads API
```
GET  /api/leads                    → Get leads
     ?sources=telegram&sources=jiji
     &freshness=24h&freshness=3d
     &limit=50
GET  /api/leads/{id}               → Lead detail
```

---

## Deployment

### Railway (Recommended)
```bash
# Deploy to Railway
railway login
railway init
railway up
```

### Docker Compose (Local)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/delta9

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash
SERPAPI_KEY=your_key

# App
APP_ENV=production
DEBUG=false
SECRET_KEY=change_me
```

---

## Directory Structure

```
delta-9-main/
├── app/
│   ├── api/
│   │   └── routes/
│   │       └── guardian.py      # System API
│   ├── core/
│   │   ├── system_guardian.py   # Self-healing watchdog
│   │   └── logging_system.py    # Structured logging
│   ├── pipeline/
│   │   └── lead_pipeline.py     # 10-stage pipeline
│   ├── scrapers/
│   │   ├── base_hardened.py     # Base scraper class
│   │   └── scraper_orchestrator.py  # Scraper manager
│   └── services/
│       └── deduplication_service.py  # Duplicate detection
├── frontend/
│   └── src/
│       └── pages/
│           └── LiveBuyersPage.jsx  # Real-time UI
├── logs/                        # Application logs
├── Dockerfile                   # Container definition
├── docker-compose.yml           # Local stack
├── railway.toml                 # Railway config
└── ARCHITECTURE.md             # This file
```

---

## Monitoring & Alerts

### Logs
- `logs/delta9.log` - Application logs (JSON)
- `logs/errors.log` - Error logs
- `logs/audit.log` - Audit trail

### Metrics
- Pipeline acceptance rate
- Scraper health status
- System resource usage
- Lead velocity (leads/minute)

### Alerts
- Scraper down > 2 minutes
- Pipeline queue > 10,000
- Error rate > 10/minute
- Database connection lost

---

## Security

### Data Protection
- Phone numbers encrypted at rest
- Source URLs verified
- No PII in logs
- Audit trail for all exports

### Access Control
- API key authentication
- Rate limiting (30 req/min)
- CORS configured
- Input sanitization

---

## Performance

### Targets
- Pipeline processing: < 100ms per lead
- Scraper restart: < 10 seconds
- API response: < 200ms
- Health check: < 5 seconds

### Scaling
- Horizontal: Multiple backend instances
- Queue: Redis for job distribution
- Database: PostgreSQL with connection pooling
- Cache: Redis for deduplication

---

## Summary

Delta-9 is built for **production reliability**:

✅ **Real Data Only** - Never generates fake leads  
✅ **Self-Healing** - Auto-recovery from failures  
✅ **Verified** - Every phone number validated  
✅ **Fresh** - Only recent leads (< 7 days)  
✅ **Traceable** - Every lead linked to source  
✅ **Resilient** - Handles scraper failures gracefully  
✅ **Monitored** - Comprehensive logging & metrics  

This is a **mission-critical lead intelligence platform** designed to run 24/7 without manual intervention.
