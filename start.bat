@echo off
chcp 65001 >nul
cls
echo.
echo ============================================================
echo   DELTA 9 SERVER
echo ============================================================
echo.
echo   Starting server on http://localhost:8000
echo.
echo   API Docs: http://localhost:8000/docs
echo   Health:   http://localhost:8000/health
echo.
echo   Press CTRL+C to stop
echo ============================================================
echo.

set PYTHONIOENCODING=utf-8
set ENVIRONMENT=development
set DATABASE_URL=sqlite:///./delta9.db
set REDIS_URL=redis://localhost:6379/0

.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
