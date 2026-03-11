# How to Start Delta-9

## Services Status

### Current Status
- Backend: Starting up...
- Frontend: Running on http://localhost:5173

## How to Start

### Step 1: Start Backend (REQUIRED FIRST)

**Double-click this file:**
```
delta-9-main/1-start-backend.bat
```

**Wait until you see:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

This may take 10-20 seconds on first start.

### Step 2: Start Frontend

**Double-click this file:**
```
delta-9-main/2-start-frontend.bat
```

**Wait until you see:**
```
Local:   http://localhost:5173/
```

### Step 3: Open Browser

Open: **http://localhost:5173**

---

## Troubleshooting

### "Nothing showing on localhost:5173"

1. Check both CMD windows are open
2. Check backend shows "Uvicorn running on http://0.0.0.0:8000"
3. Check frontend shows "http://localhost:5173/"
4. If backend shows error, wait 10 more seconds
5. If still not working, close both windows and try again

### "Port already in use"

Close all CMD windows, then:
```powershell
Get-Process python*, node* | Stop-Process -Force
```
Then start again.

### "Backend starts but frontend shows error"

Check the frontend window for errors.
Make sure backend is fully started before starting frontend.

---

## View Scrapers

Once running, go to:
- http://localhost:5173/agents (Frontend)
- http://localhost:8000/api/guardian/scrapers (API)

You should see 14 scrapers listed.

---

## Quick Check

Open PowerShell and run:
```powershell
curl http://localhost:8000/api/guardian/ping
```

Should return:
```json
{"status":"ok","timestamp":"..."}
```
