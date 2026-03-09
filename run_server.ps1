# Delta 9 Server Startup Script
$env:PYTHONIOENCODING = "utf-8"
$env:ENVIRONMENT = "development"
$env:DATABASE_URL = "sqlite:///./delta9.db"
$env:REDIS_URL = "redis://localhost:6379/0"

Set-Location $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  DELTA 9 SERVER STARTING" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Starting server on http://localhost:8000" -ForegroundColor Green
Write-Host ""
Write-Host "  API Docs:   http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "  Health:     http://localhost:8000/health" -ForegroundColor Yellow
Write-Host "  Search API: http://localhost:8000/api/search" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Press CTRL+C to stop" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
