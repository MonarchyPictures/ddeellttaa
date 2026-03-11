$env:DATABASE_URL="sqlite:///./delta9.db"
$env:REDIS_URL=""
$env:APP_ENV="development"
$env:DEBUG="true"
$env:SECRET_KEY="local-dev-key"
$env:PYTHONPATH="."

Write-Host "Starting Delta-9 Backend..." -ForegroundColor Green
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
