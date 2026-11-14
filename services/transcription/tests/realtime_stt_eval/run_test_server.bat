@echo off
setlocal
cd /d "%~dp0"
echo ====================================================================
echo  AssemblyAI Universal-3.6 Pro Realtime Test Server
echo  Isolated: tests\realtime_stt_eval\
echo  Port: 8003
echo  Production (port 8000) is UNTOUCHED.
echo ====================================================================

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Test virtualenv not found. Run setup first.
    exit /b 1
)

.venv\Scripts\python.exe verify_isolation.py
if errorlevel 1 (
    echo ISOLATION CHECK FAILED. Aborting.
    exit /b 1
)

echo.
echo Starting test backend at http://127.0.0.1:8003
echo.
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8003 --reload
pause
