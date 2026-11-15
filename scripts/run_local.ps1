# Clinical Scribe Platform - Local Development Launcher
# Starts Dashboard Backend, Clinical NLP, and Mock EHR with SQLite fallbacks.

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Clinical Scribe Unified Platform - Local Process Launcher" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Set environment defaults for local execution
$env:AUTH_DISABLED = "true"
$env:WHISPER_DEVICE = "cpu"
$env:ENABLE_EXTERNAL_LLM = "false"
$env:DISABLE_MODEL_WARMUP = "true"
$env:ALLOW_REMOTE_LLM = "false"
$env:DATABASE_URL = "sqlite:///clinical_scribe.db"
$env:EHR_DATABASE_URL = "sqlite:///mock_ehr.db"
$env:CLINICAL_NLP_URL = "http://localhost:8002"
$env:TRANSCRIPTION_URL = "http://localhost:8003"
$env:MOCK_EHR_URL = "http://localhost:8001"

Write-Host "Local Ports:" -ForegroundColor Yellow
Write-Host "  - Dashboard Backend:     http://localhost:8000 (API Docs: http://localhost:8000/api/docs)"
Write-Host "  - Mock EHR Service:      http://localhost:8001 (Docs: http://localhost:8001/docs)"
Write-Host "  - Clinical NLP Service:  http://localhost:8002 (Docs: http://localhost:8002/docs)"
Write-Host "  - Transcription Service: http://localhost:8003 (Docs: http://localhost:8003/docs)"
Write-Host "  - React Frontend:        http://localhost:3000 (run 'npm run dev' inside frontend/)"

Write-Host "`nTo start individual services in separate terminal tabs:" -ForegroundColor Cyan
Write-Host "  Tab 1 (Dashboard):     cd backend\dashboard; python -m uvicorn app.main:app --port 8000 --reload"
Write-Host "  Tab 2 (Clinical NLP):  cd services\clinical_nlp; python -m uvicorn app.main:app --port 8002 --reload"
Write-Host "  Tab 3 (Transcription): cd services\transcription; python -m uvicorn app.main:app --port 8003 --reload"
Write-Host "  Tab 4 (Mock EHR):      cd mock_ehr; python -m uvicorn api.main:app --port 8001 --reload"
Write-Host "  Tab 5 (Frontend):      cd frontend; npm run dev"
Write-Host "==========================================================" -ForegroundColor Cyan
