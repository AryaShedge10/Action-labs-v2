@echo off
REM ============================================================
REM NVIDIA NeMo Realtime Test Backend Launch Script
REM tests/realtime_nvidia/run_test_backend.bat
REM
REM Starts the FastAPI test backend on port 8004.
REM REQUIRES: NeMo-Speech.cpp server already running (run_nemo_server.bat)
REM           OR use simulation mode for UI testing without GPU.
REM
REM NO global installs. Uses .venv inside tests/realtime_nvidia/.
REM Production (port 8000) is NEVER touched.
REM ============================================================

setlocal

set TEST_ROOT=%~dp0
set VENV=%TEST_ROOT%.venv

echo ============================================================
echo  NVIDIA NeMo Realtime Test Backend
echo  Port:    8004
echo  Venv:    %VENV%
echo  WARNING: Run run_nemo_server.bat FIRST
echo ============================================================
echo.

REM ---- Step 1: Check venv ----
if not exist "%VENV%\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv "%VENV%"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        echo Make sure Python 3.11+ is installed.
        pause
        exit /b 1
    )
    echo [INFO] Installing test dependencies...
    "%VENV%\Scripts\pip" install -r "%TEST_ROOT%backend\requirements.txt"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
)

REM ---- Step 2: Load .env ----
set ENV_FILE=%TEST_ROOT%.env
if exist "%ENV_FILE%" (
    echo [INFO] Loading config from %ENV_FILE%
)

REM ---- Step 3: Verify Python is test-isolated ----
echo [INFO] Python: %VENV%\Scripts\python.exe
"%VENV%\Scripts\python.exe" -c "import sys; print('[INFO] sys.prefix:', sys.prefix)"

REM ---- Step 4: Start backend ----
echo.
echo [INFO] Starting test backend...
echo [INFO] Open: http://127.0.0.1:8004
echo [INFO] API docs: http://127.0.0.1:8004/docs
echo.
echo  To use simulation mode (no GPU required):
echo    POST http://127.0.0.1:8004/test/realtime/start?simulation=true
echo ============================================================

cd /d "%TEST_ROOT%"
"%VENV%\Scripts\uvicorn" backend.app.main:app --host 127.0.0.1 --port 8004 --reload

endlocal
