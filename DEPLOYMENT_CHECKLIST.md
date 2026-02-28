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
| `SCRAPER_CONCURRENCY` | `3` | Max parallel scrapers |

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
│  → Returns 10 query variants                                 │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  run_scrapers_parallel(scrapers, queries)                    │
│  → 11 scrapers, max 3 concurrent, 25s timeout               │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  process_high_recall_results(raw_results)                    │
│  → Deduplicate → Score (0.25 threshold) → Top 20            │
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
| Scraper count | 11 |
| Query variants | 10 |
| Intent threshold | 0.25 |
| Max results | 20 |
| Response time | < 60s |
| Error rate | 0% |

---

**System is production-ready. Deploy with confidence.** 🚀
