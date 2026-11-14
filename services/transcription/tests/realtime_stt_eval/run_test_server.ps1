$ErrorActionPreference = "Continue"

$TestDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $TestDir

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " AssemblyAI Universal-3.6 Pro Realtime Test Server" -ForegroundColor Green
Write-Host " Port: 8003 | Isolated: tests/realtime_stt_eval/" -ForegroundColor Yellow
Write-Host " Production (port 8000) is UNTOUCHED." -ForegroundColor Magenta
Write-Host "====================================================================" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "ERROR: Test virtualenv not found." -ForegroundColor Red
    exit 1
}

Write-Host "`nRunning isolation verification..." -ForegroundColor Yellow
& ".venv\Scripts\python.exe" verify_isolation.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ISOLATION CHECK FAILED. Aborting." -ForegroundColor Red
    exit 1
}

Write-Host "`nStarting test backend at http://127.0.0.1:8003" -ForegroundColor Green
Write-Host "API Key Source: tests/realtime_stt_eval/.env`n" -ForegroundColor Yellow

& ".venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8003 --reload
