# Quick Start Script for Windows
# Run this to start the Conut AI Unified System

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "   CONUT AI UNIFIED OPERATIONS SYSTEM - QUICK START" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# Check if Python is available
Write-Host "[1/4] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   ✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Python not found. Please install Python 3.8+ first." -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists
Write-Host "`n[2/4] Checking virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "   ✓ Virtual environment found" -ForegroundColor Green
} else {
    Write-Host "   ⚠ Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "   ✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "`n[3/4] Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
Write-Host "   ✓ Virtual environment activated" -ForegroundColor Green

# Install/check dependencies
Write-Host "`n[4/4] Checking dependencies..." -ForegroundColor Yellow
$pipList = pip list 2>&1
if ($pipList -match "fastapi" -and $pipList -match "uvicorn") {
    Write-Host "   ✓ Core dependencies found" -ForegroundColor Green
} else {
    Write-Host "   ⚠ Installing dependencies (this may take a few minutes)..." -ForegroundColor Yellow
    
    # Use clean requirements if available, otherwise use regular
    if (Test-Path "requirements_clean.txt") {
        pip install -r requirements_clean.txt --quiet
    } else {
        pip install -r requirements.txt --quiet
    }
    Write-Host "   ✓ Dependencies installed" -ForegroundColor Green
}

# Start the server
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "   STARTING UNIFIED API SERVER" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

Write-Host "Server will be available at:" -ForegroundColor Yellow
Write-Host "  • Main API: http://localhost:8000" -ForegroundColor White
Write-Host "  • API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  • Alt Docs: http://localhost:8000/redoc`n" -ForegroundColor White

Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Gray

# Start the unified system
python main.py
