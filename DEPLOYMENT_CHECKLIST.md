# DEPLOYMENT CHECKLIST — Final Clean Architecture

## ✅ PRE-DEPLOYMENT VERIFICATION

### 1. Grep Check (Run Locally)

```bash
# Must return ZERO results (except comments)
grep -r "app\.engine" --include="*.py" .
grep -r "LeadValidator" --include="*.py" .
grep -r "AgentRawLead" --include="*.py" .
grep -r "scrape_platform_task" --include="*.py" .
grep -r "_estimate_competition" --include="*.py" .
grep -r "SEARCH_ENGINE" --include="*.py" .
grep -r "BUYER_CLASSIFIER" --include="*.py" .
```

**Current Status:** ✅ All clean (only comments in log files)

---

### 2. Environment Variables (Railway)

#### ✅ KEEP These

| Variable | Value | Purpose |
|----------|-------|---------|
| `HIGH_RECALL_MODE` | `true` | Enable broad query generation |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Celery broker |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | PostgreSQL connection |
| `SERPAPI_API_KEY` | `your_key` | SerpAPI access |
| `BRAVE_API_KEY` | `your_key` | Brave Search API (optional) |
| `LIGHT_SCRAPER_CONCURRENCY` | `4` | Max parallel API-based scrapers |
| `HEAVY_SCRAPER_CONCURRENCY` | `2` | Max parallel Playwright scrapers |
| **TOTAL MAX** | **4** | **Never exceed 4 on Railway** |
| `DOMAIN_COOLDOWN_SECONDS` | `10` | Min seconds between same domain requests |

#### ❌ REMOVE These (Legacy)

| Variable | Status |
|----------|--------|
| `LIMIT_SCRAPERS` | Keep but set to `false` |
| `LEGACY_ENGINE_MODE` | Not found — OK |
| `OLD_PIPELINE_MODE` | Not found — OK |
| `COMPETITION_SCORING` | Not found — OK |

#### ⚠️ OPTIONAL These

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEBUG_ACCEPT_ALL` | `false` | Bypass scoring (debug only) |
| `CACHE_TTL_SECONDS` | `600` | Cache duration |
| `TELEGRAM_API_ID` | — | Telegram scraper |
| `TELEGRAM_API_HASH` | — | Telegram scraper |

---

### 3. Railway Service Settings

```yaml
# Build Command
pip install -r requirements.txt

# Start Command
uvicorn app.main:app --host 0.0.0.0 --port $PORT

# Health Check Path
/api/health
```

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Clear Build Cache

1. Railway Dashboard → Your Service
2. Settings → Deploy
3. Click "Clear Build Cache"
4. Redeploy

### Step 2: Verify Scraper Registration

Check logs for:
```
SCRAPER REGISTRY SUMMARY
Total registered: 11
Active: 11
  TIER 1 [1000] serpapi
  TIER 1 [ 950] google_cse
  TIER 2 [ 900] telegram
  ...
```

### Step 3: Test Search

```bash
curl -X POST https://your-app.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Paint Kenya", "location": "Kenya"}'
```

**Expected Log Output:**
```
🔍 High Recall Search: 'Paint Kenya' in 'Kenya'
Generated 10 high-recall queries: [...]
Using 11 scrapers: [...]
Query '...' returned X results
Results after dedup: XX
Final leads after scoring: XX
[API RESPONSE DEBUG] Returning XX leads
```

### Step 4: Verify No Errors

**Should NOT see:**
```
❌ No scraper found for platform
❌ LeadValidator object has no attribute
❌ AgentRawLead
❌ _estimate_competition
```

**SHOULD see:**
```
✅ Registered: serpapi (priority=1000)
✅ Saved lead from ...
[API RESPONSE DEBUG] Returning X leads
```

---

## 📋 POST-DEPLOYMENT CHECKLIST

- [ ] Build cache cleared
- [ ] All 11 scrapers registered
- [ ] Test search: "Paint Kenya" returns leads
- [ ] Frontend shows leads
- [ ] No LeadValidator errors in logs
- [ ] No AgentRawLead errors in logs
- [ ] No competition scoring errors
- [ ] Agent execution works (if tested)

---

## 🔍 TROUBLESHOOTING

### Issue: "Using 3 scrapers" instead of 11
**Cause:** `LIMIT_SCRAPERS=true`  
**Fix:** Set `LIMIT_SCRAPERS=false` in Railway env vars

### Issue: "No leads found"
**Check:** Logs for `[FILTER DEBUG]`  
**Fix:** If raw results > 0 but scored = 0, lower threshold or check intent scoring

### Issue: "Frontend empty"
**Check:** Browser console for `[FRONTEND]` logs  
**Fix:** Verify API response has `results` array

### Issue: "scrape_platform_task not found"
**Cause:** Old code cached  
**Fix:** Clear Railway build cache and redeploy

---

## 🛡️ PRODUCTION HARDENING

### Domain Cooldown System
Prevents rapid-fire blocks by enforcing minimum delay between requests to same domain:
```python
LAST_DOMAIN_HIT = {}
DOMAIN_COOLDOWN_SECONDS = 10  # Configurable via env var

def domain_allowed(domain):
    if now - last_hit < 10:
        return False  # On cooldown
    return True
```

### Kenya Vertical-Specific Query Templates

Generic queries are weak. System **auto-detects vertical** and optimizes:

| Vertical | Detected By | Special Signals |
|----------|-------------|-----------------|
| **Real Estate** | house, apartment, bedroom, rent, bedsitter | `2br`, `3br`, `cash buyer`, `owner direct`, Nairobi areas |
| **Vehicles** | toyota, car, gari, honda, nissan, bmw | `gari`, `automatic`, `manual`, budget ranges (100k-2m) |
| **Electronics** | iphone, samsung, laptop, phone, tv | `used`, `refurbished`, `box`, `warranty` |
| **Services** | plumber, electrician, fundi, mechanic | `fundi wa`, `urgently`, `needed today` |
| **General** | (fallback) | Standard 10 buyer signals |

**Real Estate Example** (`product="2 bedroom"`):
```python
"2 bedroom" "Kileleshwa" "looking for"
"2 bedroom" "Rongai" "natafuta"
"2 bedroom" "Syokimau" "for rent"
"2 bedroom" "Nairobi" "cash buyer"
"2 bedroom" "Nairobi" "owner direct"
"bedsitter" "Rongai" "budget 15k"
# ... 50+ combinations with area-specific targeting
```

**Vehicle Example** (`product="Toyota Corolla"`):
```python
"Toyota Corolla" "Kenya" "looking for"
"Toyota Corolla" "Kenya" "natafuta"
"Toyota Corolla" "Kenya" "100k"
"Toyota Corolla" "Kenya" "200k budget"
```

**Service Example** (`product="plumber"`):
```python
"plumber" "Nairobi" "fundi wa"
"plumber" "Nairobi" "urgently"
"fundi wa plumber" "Nairobi"
"plumber" "Nairobi" "any recommendations"
```

**Generic Fallback** (for non-vertical products):
```python
site:facebook.com "pipes" "Kenya" "looking for"
site:t.me "pipes" "Kenya" "natafuta"
site:jiji.co.ke "pipes" "Kenya" "budget"
```

### Scraper Classification

**Light Scrapers** (API-based, fast, low memory):
- `serpapi` — SerpAPI (priority: 1000)
- `yahoo` — Yahoo Search (priority: 920)
- `yandex` — Yandex Search (priority: 910)
- `brave` — Brave Search (priority: 900)
- `telegram` — Telegram API (priority: 850)
- `google_cse` — Google Custom Search (priority: 850) — FALLBACK
- `duckduckgo` — DDG API (priority: 100)

**Heavy Scrapers** (Playwright-based, slow, high memory):
- `facebook` / `facebook_groups`
- `twitter`
- `jiji`
- `pigiame`
- `google_maps`
- `whatsapp_groups`
- `kenyan_forums`

### Anti-429 Measures

1. **Jitter**: Random 0.8-2.5s delay before each request
2. **Exponential Backoff**: 2 retries with doubling delays (3s → 6s)
3. **Rate Limit Detection**: Catches "429", "rate limit", "too many requests"
4. **User-Agent Rotation**: 13 rotating UAs (Chrome, Firefox, Safari, Edge)
5. **Domain Cooldown**: 10s minimum between requests to same domain (prevents rapid-fire blocks)

---

## 🎯 EXPECTED FINAL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│  USER / AGENT                                                │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  POST /api/search  │  Celery run_agent_task                   │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  generate_high_recall_queries(query, location)               │
│  → Returns 42 query variants (site × signal combinations)    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  run_scrapers_parallel(scrapers, queries)                    │
│  → Light scrapers: max 6 concurrent (API-based)              │
│  → Heavy scrapers: max 2 concurrent (Playwright)             │
│  → Anti-429: jitter + exponential backoff                    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  process_high_recall_results(raw_results)                    │
│  → Deduplicate → Score (0.15 threshold) → Top 20            │
│  → Budget boost: ksh/kes/budget = +0.20                     │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Save to DB → Return JSON                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Scraper count | 14 |
| Query variants | 42 |
| Intent threshold | 0.15 |
| Max results | 20 |
| Light concurrency | 4 |
| Heavy concurrency | 2 |
| **Total max** | **4** |
| Response time | < 60s |
| Error rate | 0% |

---

## 🔥 FINAL RAILWAY PRODUCTION SETTINGS

### Single-Service Deployment (Simple, Limited)
```bash
# Required
HIGH_RECALL_MODE=true
LIGHT_SCRAPER_CONCURRENCY=4
HEAVY_SCRAPER_CONCURRENCY=2
DOMAIN_COOLDOWN_SECONDS=10
WORKER_MODE=true

# API Keys
SERPAPI_API_KEY=your_key_here
BRAVE_API_KEY=your_key_here

# Database & Redis
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

### Multi-Service Deployment (Recommended, Scalable)

**API Service:**
```bash
WORKER_MODE=false
SCRAPER_CONCURRENCY=2
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
HIGH_RECALL_MODE=true
```

**Worker Service:**
```bash
WORKER_MODE=true
SCRAPER_CONCURRENCY=4
LIGHT_SCRAPER_CONCURRENCY=4
HEAVY_SCRAPER_CONCURRENCY=2
DOMAIN_COOLDOWN_SECONDS=10
PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SERPAPI_API_KEY=your_key_here
BRAVE_API_KEY=your_key_here
HIGH_RECALL_MODE=true
```

**Scheduler Service:**
```bash
WORKER_MODE=false
REDIS_URL=${{Redis.REDIS_URL}}
HIGH_RECALL_MODE=true
```

**Worker Service (Rate Limiting):**
```bash
# Per-worker rate limit (prevents 429 explosion when scaling)
GLOBAL_REQUEST_LIMIT=30  # requests per minute per worker
```

**⚠️ CRITICAL: Never exceed 4 total concurrent scrapers on Railway**

### Auto-Scaling Strategy

**Scale Workers First, Not API:**
```bash
# Check queue depth
redis-cli LLEN celery

# Scale workers horizontally (not API)
railway scale --service worker --replicas 3

# API stays at 1 replica (it's lightweight)
```

**Scaling Math:**
| Workers | Total Req/Min | Safe? |
|---------|---------------|-------|
| 1 | 30 | ✅ Yes |
| 3 | 90 | ✅ Yes |
| 5 | 150 | ⚠️ Monitor |

**See `RAILWAY_SCALING_GUIDE.md` for full multi-service setup**

---

## 🧠 SaaS-Grade Lead Engine Features

### Query Intelligence Engine

Transforms simple queries into comprehensive search strategies:

```python
# User types: "pipes"
# System expands to 20+ variants:
# - "pvc pipes" "Nairobi"
# - "mabomba" "Nairobi" 
# - "plumbing pipes" "Westlands"
# - "water pipes" "Kilimani"
```

**Environment Variables:**
```bash
USE_QUERY_INTELLIGENCE=true
```

### Weighted Lead Scoring

Deterministic but tunable scoring model:

```bash
# Tunable weights (sum to 1.0)
SCORE_WEIGHT_INTENT=0.30
SCORE_WEIGHT_URGENCY=0.20
SCORE_WEIGHT_BUDGET=0.20
SCORE_WEIGHT_LOCATION=0.10
SCORE_WEIGHT_CONTACT=0.10
SCORE_WEIGHT_AUTHENTICITY=0.10
```

**Score Formula:**
```
score = (intent_weight × intent_score) +
        (urgency_weight × urgency_score) +
        (budget_weight × budget_score) +
        (location_weight × location_score) +
        (contact_weight × contact_score) +
        (authenticity_weight × authenticity_score)
```

**See `SAAS_LEAD_ENGINE.md` for full documentation**

---

## 📊 Business Intelligence Layer

### Advanced Deduplication

Multi-signal deduplication beyond URL matching:

```bash
# Enable advanced dedup
USE_ADVANCED_DEDUP=true
TEXT_SIMILARITY_THRESHOLD=0.75
PHONE_MATCH_CONFIDENCE=0.90
```

**Signals:**
| Signal | Method | Confidence |
|--------|--------|------------|
| URL | Exact match | 100% |
| Phone | Normalized + text sim | 90% |
| Text | 75% fuzzy match | 80% |

### Intelligence Dashboard API

```bash
# Full dashboard
GET /api/dashboard/intelligence

# Individual components
GET /api/dashboard/heatmap              # Buyer heatmap by county
GET /api/dashboard/budget-distribution  # Budget histogram
GET /api/dashboard/product-demand       # Top products
```

**Visualizations:**
- 📍 Buyer heatmap by county (Nairobi vs Mombasa vs Kisumu)
- 💰 Budget distribution (0-50K, 50K-100K, 100K-500K, etc.)
- ⏰ Urgency trends (time series)
- 📈 Top product demand (ranked list)

**See `BUSINESS_INTELLIGENCE.md` for full documentation**

---

## 🏗️ RAILWAY SCALING STRATEGY (Multi-Service)

**⚠️ Single-service deployment will crash on heavy scraping!**

### Recommended Production Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RAILWAY PROJECT                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Service 1  │  │   Service 2  │  │   Service 3  │      │
│  │     API      │  │    Worker    │  │  Scheduler   │      │
│  │   FastAPI    │  │    Celery    │  │   (Beat)     │      │
│  │  • Public    │  │  • Scrape    │  │  • Trigger   │      │
│  │  • No PW     │  │  • Playwright│  │  • Schedule  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │              │
│         └─────────────────┼──────────────────┘              │
│                           ▼                                 │
│              ┌─────────────────────┐                       │
│              │  Redis + Postgres   │                       │
│              │  (Railway Addons)   │                       │
│              └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### Service Configuration

| Service | Type | RAM | Purpose | Start Command |
|---------|------|-----|---------|---------------|
| **API** | Web | 512MB | FastAPI endpoints | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Worker** | Worker | 2GB | Scraping + scoring | `celery -A app.core.celery_app worker --concurrency=2` |
| **Scheduler** | Worker | 256MB | Agent triggers | `celery -A app.core.celery_app beat` |
| **Redis** | Addon | 256MB | Task queue | Railway managed |
| **Postgres** | Addon | 1GB | Database | Railway managed |

### Why Multi-Service?

| Problem | Single Service | Multi-Service |
|---------|---------------|---------------|
| Memory | Playwright crashes API | API stays lightweight |
| Scaling | Can't scale independently | Scale workers horizontally |
| Reliability | One crash kills everything | Services isolated |
| Debugging | Mixed logs | Clear service boundaries |

### Deployment

```bash
# See full guide: RAILWAY_SCALING_GUIDE.md
railway add --service api
railway add --service worker  
railway add --service scheduler
railway add --database postgres
railway add --redis redis
```

---

## 🚨 FINAL REALITY CHECK — If Search Returns 0 Leads

**It is 100% ONE of these four issues:**

### 1. All Search Engines Blocked (429)
**Symptoms:**
- Logs show "429", "rate limit", "too many requests"
- All scrapers returning empty
- `RateLimitError` in logs

**Diagnose:**
```bash
# Check logs for 429 errors
grep -i "429\|rate.*limit\|blocked" railway_logs.txt
```

**Fix:**
- Increase `DOMAIN_COOLDOWN_SECONDS` to 15 or 20
- Check if IP is blacklisted (deploy from different region)
- Verify User-Agent rotation is working
- Reduce `LIGHT_SCRAPER_CONCURRENCY` to 2

---

### 2. Intent Threshold Too Strict
**Symptoms:**
- Logs show "Raw results: X" but "Scored ≥0.15: 0"
- Lots of results found but all filtered out
- `[FILTER DEBUG]` shows 0 passing

**Diagnose:**
```bash
# Check filter debug logs
grep "FILTER DEBUG" railway_logs.txt
# Should show: "Input: 50 raw | Scored ≥0.15: 0"
```

**Quick Test:**
```bash
# Temporarily lower threshold to 0.05 in code
# If leads appear → threshold was too strict
```

**Fix:**
- Threshold already lowered to **0.15** (was 0.25)
- If still 0 results, temporarily set `DEBUG_ACCEPT_ALL=true`
- Check intent scoring logic in `calculate_kenyan_intent_score()`

---

### 3. Frontend Overwriting Response
**Symptoms:**
- Backend logs show "Returning X leads"
- Browser console shows empty results
- Frontend shows "No leads found"

**Diagnose:**
```javascript
// In browser console after search
console.log('[FRONTEND] data:', data);
console.log('[FRONTEND] results:', data.results);
console.log('[FRONTEND] leads:', data.leads);
```

**Fix:**
- Check `Dashboard.jsx` — ensure using `data.results` not `data.leads`
- Verify no `setLeads([])` happening after search
- Ensure `setLeads(data.results || [])` in handleSearch

---

### 4. DB Not Committing
**Symptoms:**
- Search works (returns leads)
- Refresh page → leads disappear
- Database shows empty or old data only

**Diagnose:**
```bash
# Check DB connection
psql $DATABASE_URL -c "SELECT COUNT(*) FROM leads;"

# Check if leads are being saved
# Should see "Saved lead from..." in logs
grep "Saved lead" railway_logs.txt
```

**Fix:**
- Check `save_leads_to_db()` function
- Verify DB session commit() is called
- Check for silent DB errors in logs

---

## ✅ PRE-DEPLOYMENT VERIFICATION COMMAND

Run this locally before deploying:

```bash
cd delta-9-main

# 1. Check no ghost code
grep -r "LeadValidator\|AgentRawLead\|scrape_platform_task" --include="*.py" .
# MUST return 0 results

# 2. Check syntax
python -m py_compile app/services/kenya_high_recall_pipeline.py
python -m py_compile app/services/parallel_scraper_runner.py

# 3. Test query generation
python -c "
from app.services.kenya_high_recall_pipeline import generate_high_recall_queries
queries = generate_high_recall_queries('pipes', 'Kenya')
print(f'Generated {len(queries)} queries')
for q in queries[:5]:
    print(f'  - {q}')
"

# 4. Test intent scoring
python -c "
from app.services.kenya_high_recall_pipeline import calculate_kenyan_intent_score
texts = [
    'Natafuta pipes Kenya urgently',  # Should be ~0.8
    'Looking for water tanks budget 50k',  # Should be ~0.7
    'For sale cheap pipes',  # Should be 0.0 (seller)
]
for t in texts:
    score = calculate_kenyan_intent_score(t)
    print(f'{score:.2f}: {t}')
"
```

---

**System is production-ready. Deploy with confidence.** 🚀
