# Delta-9 Service Starter
$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DELTA-9 SERVICE STARTER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Environment variables
$env:DATABASE_URL = "sqlite:///./delta9.db"
$env:REDIS_URL = ""
$env:APP_ENV = "development"
$env:DEBUG = "true"
$env:SECRET_KEY = "local-dev-key"
$env:PYTHONPATH = "."
$env:VITE_API_URL = "http://localhost:8000"

# Function to test connection
function Test-Connection {
    param($Port, $Name)
    try {
        $conn = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue
        if ($conn.TcpTestSucceeded) {
            Write-Host "  [OK] $Name is running on port $Port" -ForegroundColor Green
            return $true
        }
    } catch {}
    return $false
}

# Check current status
Write-Host "Checking current status..." -ForegroundColor Yellow
$backendRunning = Test-Connection -Port 8000 -Name "Backend"
$frontendRunning = Test-Connection -Port 5173 -Name "Frontend"

if ($backendRunning -and $frontendRunning) {
    Write-Host ""
    Write-Host "Both services already running!" -ForegroundColor Green
    Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Cyan
    Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
    Write-Host ""
    start http://localhost:5173
    exit
}

# Start Backend
if (-not $backendRunning) {
    Write-Host ""
    Write-Host "[STARTING] Backend on http://localhost:8000..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd" -ArgumentList "/k", "title BACKEND && cd /d `"$PWD`" && .venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" -WindowStyle Normal
    
    Write-Host "  Waiting for backend to start..." -ForegroundColor Gray
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Connection -Port 8000 -Name "Backend") { break }
    }
}

# Start Frontend
if (-not $frontendRunning) {
    Write-Host ""
    Write-Host "[STARTING] Frontend on http://localhost:5173..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd" -ArgumentList "/k", "title FRONTEND && cd /d `"$PWD\frontend`" && npm run dev" -WindowStyle Normal
    
    Write-Host "  Waiting for frontend to start..." -ForegroundColor Gray
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Connection -Port 5173 -Name "Frontend") { break }
    }
}

# Final check
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  STATUS CHECK" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

$backendRunning = Test-Connection -Port 8000 -Name "Backend"
$frontendRunning = Test-Connection -Port 5173 -Name "Frontend"

Write-Host ""
if ($backendRunning -and $frontendRunning) {
    Write-Host "SUCCESS! Both services are running." -ForegroundColor Green
    Write-Host ""
    Write-Host "Frontend:  http://localhost:5173" -ForegroundColor Cyan
    Write-Host "Backend:   http://localhost:8000" -ForegroundColor Cyan
    Write-Host "API Docs:  http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Opening browser..." -ForegroundColor Yellow
    start http://localhost:5173
} else {
    Write-Host "WARNING: Some services may not have started correctly." -ForegroundColor Red
    if (-not $backendRunning) { Write-Host "  - Backend is NOT running" -ForegroundColor Red }
    if (-not $frontendRunning) { Write-Host "  - Frontend is NOT running" -ForegroundColor Red }
}

Write-Host ""
Write-Host "Press any key to close this window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
