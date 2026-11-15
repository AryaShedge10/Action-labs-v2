# Clinical Scribe Platform - Windows Setup Script
# Configures Python dependencies, Node dependencies, and creates local directories.

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Clinical Scribe Unified Platform - Windows Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Python
Write-Host "`n[1/4] Checking Python environment..." -ForegroundColor Yellow
$pyVer = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python 3.10+ is required but not found." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Detected: $pyVer" -ForegroundColor Green

# Install Core Python requirements
Write-Host "`n[2/4] Installing Python requirements..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn pydantic sqlalchemy reportlab pytest scipy soundfile pydub python-multipart

# Check Node and npm
Write-Host "`n[3/4] Checking Node.js and installing Frontend dependencies..." -ForegroundColor Yellow
$nodeVer = node --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Detected Node: $nodeVer" -ForegroundColor Green
    Push-Location "frontend"
    npm ci
    Pop-Location
} else {
    Write-Host "[WARN] Node.js is not found on PATH. Frontend build requires Node 18+." -ForegroundColor Yellow
}

# Create .env if missing
Write-Host "`n[4/4] Checking .env configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[OK] Created .env from .env.example" -ForegroundColor Green
} else {
    Write-Host "[OK] Existing .env file found" -ForegroundColor Green
}

# Ensure runtime directories exist
New-Item -ItemType Directory -Force -Path "output" | Out-Null
New-Item -ItemType Directory -Force -Path "data/store" | Out-Null

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " Setup complete! Start application using scripts\run_local.ps1" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
