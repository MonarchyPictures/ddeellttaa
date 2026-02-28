# FINAL VERIFICATION CHECKLIST

## ✅ SECTION 6 — FRONTEND OVERRIDE CHECK

### Dashboard.jsx Status

| Check | Result |
|-------|--------|
| Auto-fetch on mount | ❌ Removed (Line 54-59 comment confirms) |
| GET /api/leads after search | ❌ Not present |
| useEffect with fetch | ❌ Not present |
| setInterval polling | ❌ Not present |

### Frontend Flow (Verified Clean)

```
User Search
    ↓
handleSearch()
    ↓
POST /api/search
    ↓
const data = await response.json()
    ↓
const results = data.results || data.leads || []
    ↓
setLeads(sorted)  ← ONLY state update
    ↓
Render LeadCards
```

### NO Override Behavior

**Old Ghost Behavior (REMOVED):**
```javascript
// REMOVED: useEffect(() => { fetchLeads() }, [])  // On mount
// REMOVED: useEffect(() => { fetchLeads() }, [searchQuery])  // On search
// REMOVED: setInterval(() => fetchLeads(), 5000)  // Polling
```

**Current Clean Behavior:**
```javascript
// Line 54-59: Confirmed removed
// NOTE: Removed auto-fetch of /api/leads on mount.
// User must search to see leads. This prevents:
// 1. Override of search results
// 2. Loading stale data
// 3. Unnecessary API calls
```

---

## ✅ SECTION 7 — FULL PIPELINE TRACE

### Expected Log Sequence (Search: "pipes Kenya")

```
============================================================
[BACKEND ROUTE] /api/search POST HIT
🔍 High Recall Search: 'pipes Kenya' in 'Kenya'

Step 1: Query Generation
├── Generated 10 high-recall queries: ["pipes Kenya", "pipes Kenya price", ...]

Step 2: Scraper Execution
├── Using 11 scrapers: ['serpapi', 'google_cse', 'telegram', ...]
├── Running query: 'pipes Kenya'
├── Query 'pipes Kenya' returned 15 results
├── ... (more queries)
└── Total raw results: ~150

Step 3: Deduplication
└── Results after dedup: ~89

Step 4: Scoring
└── [FILTER DEBUG] Input: 89 raw | Scored ≥0.25: 25 | Top 20: 20

Step 5: Return Response
├── [API RESPONSE DEBUG] Returning 20 leads
└── JSON Response: {results: [...], count: 20}

Step 6: Background DB Save
└── Saved 20 new leads to DB (Background Task)
============================================================
```

### Verification Steps

1. **Search "pipes Kenya"**
   ```bash
   curl -X POST https://your-app.railway.app/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "pipes Kenya", "location": "Kenya"}'
   ```

2. **Check Logs for ALL Steps:**
   - [ ] `Generated 10 high-recall queries`
   - [ ] `Using 11 scrapers`
   - [ ] `Query '...' returned X results`
   - [ ] `Results after dedup: X`
   - [ ] `[FILTER DEBUG] Scored ≥0.25: X`
   - [ ] `[API RESPONSE DEBUG] Returning X leads`
   - [ ] `Saved X new leads to DB`

3. **Verify DB Write:**
   ```bash
   curl https://your-app.railway.app/api/leads?limit=20
   ```
   - [ ] Returns same X leads as search

4. **Check for NO Ghost Logs:**
   - [ ] ❌ `app.engine.search_engine`
   - [ ] ❌ `LeadValidator`
   - [ ] ❌ `AgentRawLead`
   - [ ] ❌ `scrape_platform_task`

---

## 🔴 IF STEPS MISSING

| Missing Step | Likely Cause | Fix |
|--------------|--------------|-----|
| Query generation | `HIGH_RECALL_MODE` not set | Set `HIGH_RECALL_MODE=true` |
| Scrapers running | `LIMIT_SCRAPERS=true` | Set `LIMIT_SCRAPERS=false` |
| Raw results = 0 | All scrapers failing | Check scraper API keys |
| Scored = 0 | Intent filtering too strict | Check `DEBUG_ACCEPT_ALL` |
| Saved = 0 | `save_leads_to_db` failing | Check DB connection |
| GET /leads empty | Transaction not committed | Check `db.commit()` |

---

## ✅ GHOST CODE FINAL STATUS

```
┌─────────────────────────────────┬────────┬─────────────────┐
│ PATTERN                         │ CODE   │ DOCUMENTATION   │
├─────────────────────────────────┼────────┼─────────────────┤
│ app.engine                      │ 0 ✅   │ Only old logs   │
│ search_engine                   │ 0 ✅   │ Only docs       │
│ LeadValidator                   │ 0 ✅   │ Only comments   │
│ AgentRawLead                    │ 0 ✅   │ Only comments   │
│ scrape_platform_task            │ 0 ✅   │ Only docs       │
│ _estimate_competition           │ 0 ✅   │ None            │
│ BUYER_CLASSIFIER                │ 0 ✅   │ None            │
│ LEGACY_ENGINE_MODE              │ 0 ✅   │ None            │
└─────────────────────────────────┴────────┴─────────────────┘
```

---

## 🚀 DEPLOYMENT COMMAND

```bash
# 1. Set environment
railway variables set HIGH_RECALL_MODE=true LIMIT_SCRAPERS=false

# 2. Clear cache and deploy
railway redeploy --clean

# 3. Test search
curl -X POST $API_URL/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "pipes Kenya", "location": "Kenya"}'

# 4. Verify logs show all 6 steps
railway logs --follow
```

---

## 📊 SUCCESS CRITERIA

| Metric | Target | Status |
|--------|--------|--------|
| Scrapers registered | 11 | ⬜ |
| Query variants | 10 | ⬜ |
| Raw results | >50 | ⬜ |
| After dedup | >30 | ⬜ |
| Scored ≥0.25 | >5 | ⬜ |
| Returned | >0 | ⬜ |
| Saved to DB | >0 | ⬜ |
| GET /leads | Same as returned | ⬜ |

**All checks must pass for clean deployment.**
