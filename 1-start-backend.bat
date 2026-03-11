@echo off
title BACKEND - Port 8000
cd /d "%~dp0"
set DATABASE_URL=sqlite:///./delta9.db
set REDIS_URL=
set APP_ENV=development
set DEBUG=true
set SECRET_KEY=local-dev-key
set PYTHONPATH=.
echo Starting Backend on http://localhost:8000
echo.
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
