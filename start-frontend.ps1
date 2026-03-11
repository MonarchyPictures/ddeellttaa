$env:VITE_API_URL="http://localhost:8000"

Write-Host "Starting Delta-9 Frontend..." -ForegroundColor Green
Write-Host "Frontend will be available at: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

cd frontend
npm run dev
