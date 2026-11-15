# Clinical Scribe Platform - Comprehensive Test Runner
# Executes test suites across root contracts, backend, clinical NLP, transcription, and frontend.

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Running Complete Clinical Scribe Test Suite" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$totalFailures = 0

# 1. Root Monorepo Integration & End-to-End Suite
Write-Host "`n[1/5] Running Root Monorepo & End-to-End Tests..." -ForegroundColor Yellow
python -m pytest tests -v -o "pythonpath=."
if ($LASTEXITCODE -ne 0) { $totalFailures++ }

# 2. Backend Dashboard Local Suite
Write-Host "`n[2/5] Running Dashboard Backend Tests..." -ForegroundColor Yellow
Push-Location "backend/dashboard"
python -m pytest tests -v
if ($LASTEXITCODE -ne 0) { $totalFailures++ }
Pop-Location

# 3. Clinical NLP Suite
Write-Host "`n[3/5] Running Clinical NLP & Safety Engine Tests..." -ForegroundColor Yellow
Push-Location "services/clinical_nlp"
python -m pytest tests/unit tests/evaluation tests/integration/test_team_c_export.py -v -o "pythonpath=."
if ($LASTEXITCODE -ne 0) { $totalFailures++ }
Pop-Location

# 4. Transcription Unit Suite
Write-Host "`n[4/5] Running Transcription & Audio Preprocessing Tests..." -ForegroundColor Yellow
Push-Location "services/transcription"
python -m pytest tests/test_alignment.py tests/test_merge.py tests/test_roles.py tests/test_utterance_manager.py tests/test_window_refiner.py -v -o "pythonpath=."
if ($LASTEXITCODE -ne 0) { $totalFailures++ }
Pop-Location

# 5. Frontend TypeScript Verification
Write-Host "`n[5/5] Running Frontend TypeScript Typecheck & Build..." -ForegroundColor Yellow
Push-Location "frontend"
npx tsc --noEmit
if ($LASTEXITCODE -ne 0) { $totalFailures++ }
npm run build
if ($LASTEXITCODE -ne 0) { $totalFailures++ }
Pop-Location

Write-Host "`n==========================================================" -ForegroundColor Cyan
if ($totalFailures -eq 0) {
    Write-Host " ALL TEST SUITES PASSED CLEANLY (0 FAILURES)" -ForegroundColor Green
    exit 0
} else {
    Write-Host " TEST RUN COMPLETED WITH $totalFailures SUITE FAILURE(S)" -ForegroundColor Red
    exit 1
}
Write-Host "==========================================================" -ForegroundColor Cyan
