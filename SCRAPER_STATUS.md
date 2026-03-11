# Scraper Status - Troubleshooting

## Current Status: ✅ 14 Scrapers Registered

All scrapers are registered and active in the system:

| Priority | Scraper | Type |
|----------|---------|------|
| 1000 | serpapi | Search API |
| 920 | yahoo | Search Engine |
| 910 | yandex | Search Engine |
| 900 | telegram | Messaging |
| 900 | brave | Search Engine |
| 850 | google_cse | Search API |
| 750 | facebook | Marketplace |
| 700 | kenyan_forums | Forums |
| 650 | twitter | Social |
| 500 | jiji | Marketplace |
| 500 | pigiame | Marketplace |
| 400 | google_maps | Maps |
| 350 | whatsapp_groups | Messaging |
| 100 | duckduckgo | Search Engine |

---

## How to View Scrapers in the UI

### Method 1: Frontend (Agents Page)
1. Start backend and frontend
2. Open http://localhost:5173
3. Click "Agents" in the top menu or bottom navigation
4. You should see the list of agents/scrapers

### Method 2: API Endpoint
1. Start backend
2. Open http://localhost:8000/api/guardian/scrapers
3. You'll see JSON with all scraper statuses

### Method 3: Health Check
1. Start backend
2. Open http://localhost:8000/api/guardian/health
3. Check the "scrapers" array in the response

---

## Quick Start

### Step 1: Double-click START-ALL.cmd
This will open two windows:
- BACKEND window (port 8000)
- FRONTEND window (port 5173)

### Step 2: Wait for "ready" messages
Backend: `Uvicorn running on http://0.0.0.0:8000`
Frontend: `Local: http://localhost:5173/`

### Step 3: View scrapers
Open http://localhost:5173/agents

---

## Common Issues

### "No scrapers showing"
**Cause**: Backend not running
**Fix**: Check the BACKEND window is open and shows "Uvicorn running"

### "Agents page is blank"
**Cause**: Frontend can't connect to backend
**Fix**: 
1. Check backend is on port 8000
2. Check frontend vite.config.js has correct proxy
3. Restart both services

### "Scraper status shows 'unknown'"
**Cause**: Guardian not initialized
**Fix**: Wait 60 seconds after backend starts for first health check

---

## API Endpoints for Scrapers

```bash
# List all scrapers
curl http://localhost:8000/api/guardian/scrapers

# Get health status (includes scrapers)
curl http://localhost:8000/api/guardian/health

# Restart a specific scraper
POST http://localhost:8000/api/guardian/scrapers/{scraper_id}/restart
```

---

## Verification

Run this to verify scrapers:
```bash
python check-scrapers.py
```

Expected output:
```
Registered scrapers: 14
  [ACTIVE] serpapi (priority: 1000)
  [ACTIVE] telegram (priority: 900)
  ...
```
