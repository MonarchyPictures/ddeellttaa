@echo off
echo ========================================
echo  DELTA-9 LOCAL DEPLOYMENT
echo ========================================
echo.

set DATABASE_URL=sqlite:///./delta9.db
set REDIS_URL=
set APP_ENV=development
set DEBUG=true
set SECRET_KEY=local-dev-key
set PYTHONPATH=.
set VITE_API_URL=http://localhost:8000

echo [1/2] Starting Backend on http://localhost:8000...
start "Delta-9 Backend" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 5 /nobreak >nul

echo [2/2] Starting Frontend on http://localhost:5173...
start "Delta-9 Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo  SERVICES STARTED!
echo ========================================
echo.
echo Frontend:  http://localhost:5173
echo Backend:   http://localhost:8000
echo API Docs:  http://localhost:8000/docs
echo.
echo Press any key to exit this window...
echo (Services will keep running)
pause >nul
