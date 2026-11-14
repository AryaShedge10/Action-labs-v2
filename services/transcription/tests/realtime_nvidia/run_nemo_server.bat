@echo off
REM ============================================================
REM NVIDIA NeMo-Speech.cpp Runtime Launch Script
REM tests/realtime_nvidia/run_nemo_server.bat
REM
REM Starts the LOCAL NeMo-Speech.cpp inference server.
REM Models are stored in tests/realtime_nvidia/models/
REM NO internet required after first model download.
REM NO API keys.
REM ============================================================

setlocal

REM Set test root to the directory containing this script
set TEST_ROOT=%~dp0

echo ============================================================
echo  NVIDIA NeMo-Speech.cpp Local Runtime
echo  Test Directory: %TEST_ROOT%
echo  Models:         %TEST_ROOT%models\
echo  Model Cache:    %TEST_ROOT%model_cache\
echo ============================================================
echo.

REM ---- Step 1: Check if nemo-speech binary is available ----
where nemo-speech >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] nemo-speech binary not found in PATH.
    echo.
    echo  NeMo-Speech.cpp must be installed first.
    echo  See: tests\realtime_nvidia\INSTALLATION_GUIDE.md
    echo.
    echo  Quick install reference:
    echo    1. Download NeMo-Speech.cpp from:
    echo       https://github.com/NVIDIA/NeMo-Speech.cpp/releases
    echo    2. Extract and add to PATH, OR run from extracted directory.
    echo    3. Run: nemo-speech pull nemotron-3.5
    echo    4. Run: nemo-speech pull nemotron-3-diarization
    echo.
    pause
    exit /b 1
)

REM ---- Step 2: Configure model directory ----
REM Direct model storage to test-local directory (Phase 9)
set NEMO_SPEECH_MODEL_DIR=%TEST_ROOT%models
set NEMO_SPEECH_CACHE_DIR=%TEST_ROOT%model_cache

echo [INFO] Model directory:  %NEMO_SPEECH_MODEL_DIR%
echo [INFO] Cache directory:  %NEMO_SPEECH_CACHE_DIR%

REM ---- Step 3: Pull models if not already downloaded ----
echo [INFO] Checking ASR model (nemotron-3.5)...
nemo-speech --model-dir "%NEMO_SPEECH_MODEL_DIR%" pull nemotron-3.5
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Model pull returned non-zero. Continuing (model may already exist).
)

echo [INFO] Checking diarization model (nemotron-3-diarization)...
nemo-speech --model-dir "%NEMO_SPEECH_MODEL_DIR%" pull nemotron-3-diarization
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Diarization model pull returned non-zero. Continuing.
)

REM ---- Step 4: Start the streaming server ----
REM
REM NeMo-Speech.cpp server options:
REM   --model        ASR model (nemotron-3.5 = nvidia/nemotron-3.5-asr-streaming-0.6b)
REM   --diarization  diarization model (nemotron-3-diarization = Streaming Sortformer)
REM   --speakers     max speakers (2 for Doctor+Patient)
REM   --latency      streaming latency mode (low_latency / very_low_latency / ultra_low_latency)
REM   --language     language code (en-US for clinical English)
REM   --ws-port      WebSocket server port (default 8888)
REM   --model-dir    model storage directory (local test dir)
REM
REM NOTE: GTX 1650 (4GB VRAM) — start with low_latency.
REM       Benchmark very_low_latency and ultra_low_latency before switching.
REM       The published NVIDIA latency figures are for H100-class hardware.

echo.
echo [INFO] Starting NeMo-Speech.cpp streaming server...
echo [INFO] ASR:          nemotron-3.5 (nvidia/nemotron-3.5-asr-streaming-0.6b)
echo [INFO] Diarization:  nemotron-3-diarization (Streaming Sortformer)
echo [INFO] Speakers:     2 (Doctor + Patient)
echo [INFO] Latency mode: low_latency
echo [INFO] Language:     en-US
echo [INFO] WS port:      8888
echo [INFO] GPU:          GTX 1650 (CUDA 13.1)
echo.
echo  Once server is ready, open a NEW terminal and run:
echo    run_test_backend.bat
echo.
echo  Then open: http://127.0.0.1:8004
echo ============================================================

nemo-speech serve ^
    --model nemotron-3.5 ^
    --diarization nemotron-3-diarization ^
    --speakers 2 ^
    --latency low_latency ^
    --language en-US ^
    --ws-port 8888 ^
    --model-dir "%NEMO_SPEECH_MODEL_DIR%"

endlocal
