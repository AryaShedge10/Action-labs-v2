# ============================================================
# NVIDIA NeMo Realtime Test Backend — PowerShell Launch Script
# tests/realtime_nvidia/run_test_backend.ps1
# ============================================================

$TestRoot  = $PSScriptRoot
$VenvDir   = Join-Path $TestRoot ".venv"
$Python    = Join-Path $VenvDir "Scripts\python.exe"
$Uvicorn   = Join-Path $VenvDir "Scripts\uvicorn.exe"
$ReqFile   = Join-Path $TestRoot "backend\requirements.txt"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " NVIDIA NeMo Realtime Test Backend" -ForegroundColor Cyan
Write-Host " Port:    8004" -ForegroundColor White
Write-Host " Venv:    $VenvDir" -ForegroundColor White
Write-Host " WARNING: Run run_nemo_server.bat FIRST in another terminal" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Create venv if needed
if (-not (Test-Path $Python)) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create venv"; exit 1 }

    Write-Host "[INFO] Installing dependencies..." -ForegroundColor Yellow
    & $VenvDir\Scripts\pip install -r $ReqFile
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install deps"; exit 1 }
    Write-Host "[OK] Dependencies installed." -ForegroundColor Green
}

Write-Host "[INFO] Python: $Python" -ForegroundColor Gray
& $Python -c "import sys; print('[INFO] sys.prefix:', sys.prefix)"

Write-Host ""
Write-Host "[INFO] Starting test backend on port 8004..." -ForegroundColor Green
Write-Host "[INFO] UI:       http://127.0.0.1:8004" -ForegroundColor Cyan
Write-Host "[INFO] API docs: http://127.0.0.1:8004/docs" -ForegroundColor Cyan
Write-Host ""

Set-Location $TestRoot
& $Uvicorn backend.app.main:app --host 127.0.0.1 --port 8004 --reload
