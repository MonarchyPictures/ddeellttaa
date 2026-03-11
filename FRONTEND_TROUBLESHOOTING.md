# Frontend Troubleshooting - Blank Page

## Problem: http://localhost:5173/ shows blank page

## Quick Solutions (Try in order)

### 1. Wait 10 Seconds
The React app might still be loading. Wait 10 seconds then refresh.

### 2. Hard Refresh
Press **Ctrl + Shift + R** (Windows/Linux) or **Cmd + Shift + R** (Mac)

### 3. Check Browser Console
1. Open http://localhost:5173/
2. Press **F12**
3. Click **Console** tab
4. Look for red error messages

Common errors:
- `Failed to load module` → Restart frontend
- `Cannot read property` → Clear cache
- `Loading chunk failed` → Hard refresh

### 4. Clear Browser Cache
1. Press **Ctrl + Shift + Delete**
2. Check "Cached images and files"
3. Click Clear
4. Refresh page

### 5. Try Different Browser
Test in Chrome, Edge, or Firefox.

### 6. Check if Services Are Running

Open PowerShell and run:
```powershell
Get-Process python*, node*
```

You should see:
- python (backend)
- node (frontend)

If not, restart them.

---

## How to Restart Everything

### Option 1: Double-click start.bat
Run `start.bat` in the delta-9-main folder.

### Option 2: Manual restart

**Terminal 1 - Backend:**
```powershell
cd delta-9-main
$env:DATABASE_URL="sqlite:///./delta9.db"
$env:APP_ENV="development"
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```powershell
cd delta-9-main/frontend
npm run dev
```

---

## Verify Services Are Working

### Test Backend
Open browser: http://localhost:8000/api/guardian/ping

Should show:
```json
{"status":"ok","timestamp":"2026-03-11T..."}
```

### Test Frontend
Open browser: http://localhost:5173

Should show: Delta-9 Dashboard

---

## Common Issues

### Issue: "Module not found" error
**Fix:**
```powershell
cd delta-9-main/frontend
npm install
```

### Issue: Port 5173 already in use
**Fix:**
```powershell
Get-Process node* | Stop-Process -Force
```

### Issue: Port 8000 already in use
**Fix:**
```powershell
Get-Process python* | Stop-Process -Force
```

### Issue: "Cannot GET /" error
**Fix:** Frontend is not running. Start it with `npm run dev`

---

## Still Not Working?

### Check Frontend Logs
```powershell
cd delta-9-main/frontend
Get-Content frontend.log -Tail 50
```

### Check Backend Logs
Look at the terminal where you started the backend.

### Reset Everything
```powershell
# Stop all processes
Get-Process python*, node* | Stop-Process -Force

# Clear npm cache
cd delta-9-main/frontend
npm cache clean --force

# Reinstall node modules
Remove-Item -Recurse -Force node_modules
npm install

# Restart
npm run dev
```

---

## Access URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | Main UI |
| Backend API | http://localhost:8000 | API Server |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Health | http://localhost:8000/api/guardian/ping | Health check |

---

## Contact

If none of these work, check:
- `DEPLOYMENT.md` for full setup
- `ARCHITECTURE.md` for system details
