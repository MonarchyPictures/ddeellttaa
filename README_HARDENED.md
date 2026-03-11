# DELTA-9 HARDENED
## Production-Grade Lead Intelligence Platform

---

## Overview

Delta-9 Hardened is a **mission-critical lead intelligence platform** designed for the Kenyan market. It discovers real buyer leads from live sources with strict validation to ensure data integrity.

**Core Principle**: NEVER generate fake data. Every lead must be traceable, verified, and real.

---

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run verification
python verify_installation.py

# Start the application
uvicorn app.main:app --reload
```

### Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### Railway Deployment
```bash
railway login
railway init
railway up
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DELTA-9 SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Scrapers → Pipeline → Database → API → Frontend               │
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │Telegram │  │  Jiji   │  │ Reddit  │  │ Facebook│           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│       └─────────────┴─────────────┴─────────────┘               │
│                     │                                           │
│              ┌──────┴──────┐                                    │
│              │   Pipeline  │  ← 10-stage validation            │
│              │  (Hardened) │                                    │
│              └──────┬──────┘                                    │
│                     │                                           │
│              ┌──────┴──────┐                                    │
│              │   Guardian  │  ← Self-healing watchdog          │
│              │  (Monitor)  │                                    │
│              └─────────────┘                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Lead Pipeline (10 Stages)

Every lead goes through strict validation:

1. **SCRAPE** - Validate input fields
2. **CLEAN** - Normalize text
3. **INTENT** - Detect buyer keywords
4. **EXTRACT** - Extract phone number
5. **VERIFY** - Validate Kenya phone format
6. **SOURCE** - Verify source attribution
7. **FRESHNESS** - Check timestamp (< 7 days)
8. **SCORE** - Calculate intent (0-100)
9. **DEDUPE** - Check for duplicates
10. **STORE** - Save to database

**Rule**: Any stage failure = lead rejection

---

## System Guardian

Self-healing watchdog that monitors:

- Scraper heartbeats (every 60s)
- Database connectivity
- Pipeline queue size
- System resources (CPU/RAM)
- API health

**Auto-Recovery**:
- Dead scraper → Auto-restart
- Stuck queue → Flush backlog
- High memory → Clear cache

---

## API Endpoints

### Guardian
```
GET  /api/guardian/health          → System health
GET  /api/guardian/scrapers        → Scraper status
POST /api/guardian/scrapers/{id}/restart
GET  /api/guardian/pipeline/stats  → Pipeline stats
GET  /api/guardian/errors          → Recent errors
```

### Leads
```
GET  /api/leads                    → Get leads
GET  /api/leads/{id}               → Lead detail
```

---

## Lead Schema

Every lead MUST have these fields:

```python
{
    "id": "lead_abc123",
    "query": "toyota vitz",
    "text": "Looking for Vitz in Nairobi",
    "phone": "+254712345678",
    "source_platform": "telegram",
    "source_name": "Kenya Cars",
    "source_url": "https://t.me/kenya_cars/123",
    "timestamp": "2026-03-11T10:00:00",
    "location": "Nairobi",
    "intent_score": 85,
    "temperature": "hot"
}
```

**Missing any field = automatic rejection**

---

## Buyer Intent Keywords

### Accepted (Buyer)
- looking for
- need
- natafuta
- anyone selling
- where can i buy
- budget ready
- urgently

### Rejected (Seller)
- selling
- available
- for sale
- price
- call me
- dm me
- inbox

---

## Phone Validation

Kenya format: `^(\+254|0)[17]\d{8}$`

Valid:
- `+254712345678`
- `0712345678`

Invalid:
- `+255712345678` (Tanzania)
- `071234567` (too short)

---

## Lead Freshness

| Class | Age | Priority |
|-------|-----|----------|
| HOT | < 24h | Highest |
| WARM | < 3 days | Medium |
| COLD | < 7 days | Low |
| STALE | > 7 days | **DISCARD** |

---

## Frontend

### Routes
- `/` - Dashboard
- `/live` - Live Buyers Feed (real-time)
- `/leads` - Leads Management
- `/agents` - Agent Configuration

### Live Buyers Feed
Apollo.io-style real-time feed showing:
- New buyer alerts with green pulse
- Source platform icons
- Intent score badges
- One-click to view source

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/delta9

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
TELEGRAM_API_ID=xxx
TELEGRAM_API_HASH=xxx
SERPAPI_KEY=xxx

# App
APP_ENV=production
DEBUG=false
SECRET_KEY=change_me
```

---

## Files Structure

```
delta-9-main/
├── app/
│   ├── pipeline/
│   │   └── lead_pipeline.py      # 10-stage pipeline
│   ├── core/
│   │   ├── system_guardian.py    # Self-healing
│   │   └── logging_system.py     # Structured logs
│   ├── scrapers/
│   │   ├── base_hardened.py      # Base scraper
│   │   └── scraper_orchestrator.py
│   ├── services/
│   │   └── deduplication_service.py
│   ├── api/routes/
│   │   └── guardian.py           # Guardian API
│   └── startup.py                # Startup sequence
├── frontend/
│   └── src/pages/
│       └── LiveBuyersPage.jsx    # Real-time UI
├── Dockerfile
├── docker-compose.yml
├── railway.toml
├── requirements.txt
└── ARCHITECTURE.md               # Full docs
```

---

## Monitoring

### Logs
- `logs/delta9.log` - Application logs (JSON)
- `logs/errors.log` - Error logs
- `logs/audit.log` - Audit trail

### Health Check
```bash
curl http://localhost:8000/api/guardian/health
```

### Statistics
```bash
curl http://localhost:8000/api/guardian/pipeline/stats
```

---

## Security

- Phone numbers validated
- Source URLs verified
- Input sanitized
- Rate limiting (30 req/min)
- Audit trail for exports

---

## Production Checklist

- [ ] Environment variables set
- [ ] Database migrated
- [ ] Redis connected
- [ ] API keys configured
- [ ] Health checks passing
- [ ] Logs directory created
- [ ] Docker tested locally
- [ ] Railway project created

---

## Support

### Documentation
- `ARCHITECTURE.md` - Full architecture
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `LIVE_BUYERS_FEED.md` - Frontend docs

### Verification
```bash
python verify_installation.py
```

---

## License

Proprietary - Delta-9 Lead Intelligence Platform

---

## Summary

Delta-9 Hardened is built for **production reliability**:

- Real data only (never generated)
- Self-healing (auto-recovery)
- Verified phones (Kenya format)
- Fresh leads (< 7 days)
- Traceable sources
- Comprehensive logging

**Designed for Kenya. Built for scale. Hardened for production.**
