@echo off
echo ============================================
echo DELTA-9 STARTING
echo ============================================
echo.

set DATABASE_URL=sqlite:///./delta9.db
set REDIS_URL=
set APP_ENV=development
set DEBUG=true
set SECRET_KEY=local-dev-key
set PYTHONPATH=.

echo [1/2] Starting BACKEND on http://localhost:8000
echo.
start "BACKEND - Port 8000" cmd /c ".venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 5 /nobreak

echo.
echo [2/2] Starting FRONTEND on http://localhost:5173
echo.
start "FRONTEND - Port 5173" cmd /c "cd frontend && npm run dev"

timeout /t 5 /nobreak

echo.
echo ============================================
echo SERVICES STARTED!
echo ============================================
echo.
echo Backend:   http://localhost:8000
echo Frontend:  http://localhost:5173
echo API Docs:  http://localhost:8000/docs
echo.
echo Opening browser...
start http://localhost:5173
start http://localhost:8000/docs
echo.
pause
