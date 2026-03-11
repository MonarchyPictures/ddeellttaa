@echo off
echo ============================================
echo DELTA-9 STARTING ALL SERVICES
echo ============================================
echo.

set DATABASE_URL=sqlite:///./delta9.db
set REDIS_URL=
set APP_ENV=development
set DEBUG=true
set SECRET_KEY=local-dev-key
set PYTHONPATH=.

echo [1/2] Starting BACKEND...
echo.
start "BACKEND - http://localhost:8000" cmd /k "cd /d %~dp0 && .venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

timeout /t 5 /nobreak >nul

echo [2/2] Starting FRONTEND...
echo.
start "FRONTEND - http://localhost:5173" cmd /k "cd /d %~dp0\frontend && npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo SERVICES STARTED
echo ============================================
echo.
echo Backend:   http://localhost:8000
echo Frontend:  http://localhost:5173
echo.
echo To see scrapers:
echo   1. Open http://localhost:5173
echo   2. Click "Agents" in the menu
echo   OR
echo   3. Open http://localhost:8000/api/guardian/scrapers
echo.
start http://localhost:5173
start http://localhost:8000/api/guardian/scrapers
echo.
pause
