#!/usr/bin/env pwsh
# Delta 9 Local Development Startup Script
# ========================================

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Delta 9 - Local Development Server" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
& .venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Green
pip install -q -r requirements.txt

# Install playwright browsers (if needed)
$playwrightInstalled = python -c "from playwright.sync_api import sync_playwright; print('OK')" 2>$null
if (-not $playwrightInstalled) {
    Write-Host "Installing Playwright browsers..." -ForegroundColor Yellow
    playwright install chromium
}

# Copy local environment file if .env doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.local..." -ForegroundColor Yellow
    Copy-Item .env.local .env
}

# Check if frontend dist exists
if (-not (Test-Path "frontend/dist")) {
    Write-Host "WARNING: Frontend build not found at frontend/dist" -ForegroundColor Red
    Write-Host "API will work, but UI will not be available." -ForegroundColor Yellow
    Write-Host "To build frontend: cd frontend && npm install && npm run build" -ForegroundColor Yellow
    Write-Host ""
}

# Start the server
Write-Host "============================================" -ForegroundColor Green
Write-Host "Starting Delta 9 API Server..." -ForegroundColor Green
Write-Host "API: http://localhost:8001" -ForegroundColor Cyan
Write-Host "Docs: http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

python main.py
