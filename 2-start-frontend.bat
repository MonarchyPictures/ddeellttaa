@echo off
title FRONTEND - Port 5173
cd /d "%~dp0\frontend"
set VITE_API_URL=http://localhost:8000
echo Starting Frontend on http://localhost:5173
echo.
npm run dev
pause
