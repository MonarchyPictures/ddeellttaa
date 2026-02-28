# Final Diagnosis Flow - No Guessing

## The 4 Numbers That Pinpoint the Exact Layer

Check these 4 exact log values to determine where leads are being lost:

---

## Step 1: Backend Filter Pipeline

### Check Railway Logs For:
```
[FILTER DEBUG] Input: 150 raw | After dedup: 89 unique | Scored ≥0.25: 3 | Top 20: 3
```

**Extract these 2 numbers:**
- `Input: X raw` = Raw results from scrapers
- `Scored ≥0.25: Y` = After intent filtering

### Decision Matrix:

| Input (X) | Scored ≥0.25 (Y) | Diagnosis | Layer |
|-----------|------------------|-----------|-------|
| 0 | 0 | **Scrapers returned nothing** | Scrapers |
| 150+ | 0 | **Intent filtering too strict** | Scoring |
| 150+ | 20+ | **Filtering OK** | Continue to Step 2 |

---

## Step 2: Backend Response

### Check Railway Logs For:
```
[API RESPONSE DEBUG] Returning 20 leads to frontend for query 'pipes'
```

**Extract this number:**
- `Returning Z leads` = What's being sent to frontend

### Decision Matrix:

| Scored ≥0.25 (Y) | Returning (Z) | Diagnosis | Layer |
|------------------|---------------|-----------|-------|
| 20 | 0 | **Response formation bug** | API Route |
| 20 | 20 | **Backend OK** | Continue to Step 3 |

---

## Step 3: Frontend Reception

### Check Browser Console (F12 → Console) For:
```
[FRONTEND] data.results length: 20
[FRONTEND] data.leads length: 20
[FRONTEND] ✓ Using data.results
```

**Extract this number:**
- `data.results length: W` = What frontend received

### Decision Matrix:

| Returning (Z) | data.results length (W) | Diagnosis | Layer |
|---------------|------------------------|-----------|-------|
| 20 | 0 | **Frontend parsing mismatch** | Response Format |
| 20 | 20 | **Frontend received data** | Continue to Step 4 |

---

## Step 4: Frontend Render

### Check Browser Console For:
```
[FRONTEND] Set leads state with 20 items
```

If `data.results length: 20` but UI shows "No buyers found":

**Diagnosis:** React state/render issue

---

## Quick Reference Decision Tree

```
                    [Input: X raw]
                          |
            +-------------+-------------+
            |                           |
         X = 0                      X > 0
            |                           |
    SCRAPERS FAILED              [Scored ≥0.25: Y]
            |                           |
            |             +-------------+-------------+
            |             |                           |
            |          Y = 0                        Y > 0
            |             |                           |
            |      FILTER TOO STRICT           [Returning: Z]
            |             |                           |
            |    Set DEBUG_ACCEPT_ALL=true     +------+------+
            |             |                    |             |
            |             |                 Z = 0        Z > 0
            |             |                    |             |
            |             |             RESPONSE BUG    [data.results: W]
            |             |                    |             |
            |             |                    |      +------+------+
            |             |                    |      |             |
            |             |                    |   W = 0        W > 0
            |             |                    |      |             |
            |             |                    |   FORMAT      RENDER
            |             |                    |   MISMATCH      BUG
            |             |                    |
            v             v                    v
       Check scraper    Check intent      Check API route
       logs, API keys   scoring rules     response formation
```

---

## Example Scenarios

### Scenario A: Scrapers Blocked
```
[FILTER DEBUG] Input: 0 raw | After dedup: 0 unique | Scored ≥0.25: 0 | Top 20: 0
[API RESPONSE DEBUG] Returning 0 leads to frontend for query 'pipes'
[FRONTEND] data.results length: 0
```
**→ FIX:** Check `LIMIT_SCRAPERS` env var, scraper API keys

---

### Scenario B: Intent Scoring Too Strict
```
[FILTER DEBUG] Input: 180 raw | After dedup: 112 unique | Scored ≥0.25: 0 | Top 20: 0
[API RESPONSE DEBUG] Returning 0 leads to frontend for query 'pipes'
[FRONTEND] data.results length: 0
```
**→ FIX:** Set `DEBUG_ACCEPT_ALL=true` to confirm, then lower threshold or fix scoring

---

### Scenario C: Response Format Mismatch
```
[FILTER DEBUG] Input: 150 raw | After dedup: 89 unique | Scored ≥0.25: 25 | Top 20: 20
[API RESPONSE DEBUG] Returning 20 leads to frontend for query 'pipes'
[FRONTEND] data.results is array: false
[FRONTEND] ✗ Neither data.results nor data.leads is valid array!
[FRONTEND] Available keys: ['message', 'count', 'status']
```
**→ FIX:** Backend sending wrong response shape

---

### Scenario D: Frontend Render Bug
```
[FILTER DEBUG] Input: 150 raw | After dedup: 89 unique | Scored ≥0.25: 25 | Top 20: 20
[API RESPONSE DEBUG] Returning 20 leads to frontend for query 'pipes'
[FRONTEND] data.results length: 20
[FRONTEND] ✓ Using data.results
(UI shows "No buyers found")
```
**→ FIX:** React state not updating, check setLeads call

---

## Exact Commands to Get Logs

### Railway Backend Logs:
```bash
# In Railway dashboard or CLI
railway logs --service api

# Or watch live
railway logs --service api --follow
```

### Browser Console:
```
1. Open your app in browser
2. Press F12 (or Cmd+Option+J on Mac)
3. Click "Console" tab
4. Run a search
5. Look for [FRONTEND] logs
```

---

## Copy-Paste Template for Reporting

```
## Diagnosis Results

| Metric | Value |
|--------|-------|
| Raw Input | ___ |
| Scored ≥0.25 | ___ |
| Returning to Frontend | ___ |
| data.results length | ___ |

## Conclusion

[ ] Scrapers failed (Input = 0)
[ ] Intent filtering too strict (Input > 0, Scored = 0)
[ ] Response bug (Scored > 0, Returning = 0)
[ ] Format mismatch (Returning > 0, data.results = 0)
[ ] Render bug (data.results > 0, UI empty)
```

Fill in the blanks with your actual log values.
