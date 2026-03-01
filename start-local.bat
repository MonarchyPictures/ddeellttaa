@echo off
REM Delta 9 Local Development Startup Script (Windows CMD)
REM =====================================================

echo ============================================
echo   Delta 9 - Local Development Server
echo ============================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q -r requirements.txt

REM Copy local environment file if .env doesn't exist
if not exist ".env" (
    echo Creating .env from .env.local...
    copy .env.local .env
)

echo ============================================
echo Starting Delta 9 API Server...
echo API: http://localhost:8001
echo Docs: http://localhost:8001/docs
echo ============================================
echo.

python main.py
