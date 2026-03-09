@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set ENVIRONMENT=development

echo.
echo   DELTA 9 DASHBOARD v3.0
echo   =====================
echo.

cd /d "%~dp0"
if exist ..\.venv\Scripts\activate.bat (
    call ..\.venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

echo   Starting Dashboard Server...
echo   URL: http://localhost:8000/dashboard
echo.

python app_dashboard.py
pause
