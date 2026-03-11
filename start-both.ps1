# Delta-9 Start Both Backend and Frontend

$env:DATABASE_URL = "sqlite:///./delta9.db"
$env:REDIS_URL = ""
$env:APP_ENV = "development"
$env:DEBUG = "true"
$env:SECRET_KEY = "local-dev-key"
$env:PYTHONPATH = "."
$env:VITE_API_URL = "http://localhost:8000"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DELTA-9 STARTING" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend is already running
$backendRunning = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($backendRunning) {
    Write-Host "[OK] Backend already running on port 8000" -ForegroundColor Green
} else {
    Write-Host "[START] Starting Backend on http://localhost:8000..." -ForegroundColor Yellow
    Start-Process -FilePath ".venv/Scripts/python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "[OK] Backend started" -ForegroundColor Green
}

# Check if frontend is already running
$frontendRunning = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($frontendRunning) {
    Write-Host "[OK] Frontend already running on port 5173" -ForegroundColor Green
} else {
    Write-Host "[START] Starting Frontend on http://localhost:5173..." -ForegroundColor Yellow
    Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory "./frontend" -WindowStyle Hidden
    Start-Sleep -Seconds 5
    Write-Host "[OK] Frontend started" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  DELTA-9 IS RUNNING!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor Cyan
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Health:    http://localhost:8000/api/guardian/ping" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press any key to stop all services..." -ForegroundColor Yellow
Write-Host ""

$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host "[STOP] Stopping services..." -ForegroundColor Yellow
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process node* -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "[OK] All services stopped" -ForegroundColor Green
