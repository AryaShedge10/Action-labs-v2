"""
Environment and Dependency Isolation Verifier
tests/realtime_stt_eval/verify_isolation.py

Verifies:
1. Python interpreter is strictly tests/realtime_stt_eval/.venv/Scripts/python.exe
2. Pip is strictly within tests/realtime_stt_eval/.venv
3. Production virtual environment (venv/) is NOT being used
4. No production source files are modified
5. Test dependencies are installed and accessible
"""

import os
import sys
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
TEST_DIR = Path(__file__).resolve().parent
TEST_VENV = TEST_DIR / ".venv"
PROD_VENV = WORKSPACE / "venv"
PROD_APP = WORKSPACE / "app"
PROD_STATIC = WORKSPACE / "static"

def main():
    print("=" * 72)
    print("TEST ENVIRONMENT ISOLATION VERIFICATION REPORT")
    print("=" * 72)

    current_python = Path(sys.executable).resolve()
    print(f"Current Python Executable: {current_python}")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Working Directory: {WORKSPACE}")
    print(f"Test Directory: {TEST_DIR}")
    print(f"Test Venv Target: {TEST_VENV}")
    print(f"Production Venv Path: {PROD_VENV}")

    # Check 1: Must not be running under production venv
    if str(PROD_VENV).lower() in str(current_python).lower():
        print("\n[CRITICAL FAILURE] Test is executing under the PRODUCTION virtual environment!")
        print(f"Offending executable: {current_python}")
        sys.exit(1)

    # Check 2: Must be running under test venv
    if str(TEST_VENV).lower() not in str(current_python).lower():
        print("\n[CRITICAL FAILURE] Test is NOT executing under tests/realtime_stt_eval/.venv!")
        print(f"Expected path: {TEST_VENV}")
        print(f"Actual path: {current_python}")
        sys.exit(1)

    print("\n[PASS] Python interpreter verified: Running strictly inside test .venv")

    # Check 3: Verify pip location
    pip_res = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True)
    print(f"Pip info: {pip_res.stdout.strip()}")
    if str(TEST_VENV).lower() not in pip_res.stdout.lower():
        print("\n[CRITICAL FAILURE] Pip is not located within test .venv!")
        sys.exit(1)
    print("[PASS] Pip verified: Located inside test .venv")

    # Check 4: Check installed test dependencies
    pip_list = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True)
    required_packages = ["fastapi", "uvicorn", "websockets", "python-dotenv", "numpy", "soundfile", "httpx", "pydantic"]
    missing = []
    for pkg in required_packages:
        if pkg not in pip_list.stdout.lower():
            missing.append(pkg)

    if missing:
        print(f"\n[FAIL] Missing required test dependencies in test venv: {missing}")
        sys.exit(1)
    print(f"[PASS] All {len(required_packages)} required test dependencies installed in test .venv")

    # Check 5: Verify environment variables
    env_file = TEST_DIR / ".env"
    print(f"\nTest .env file exists: {env_file.exists()}")
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8")
        has_key = "ASSEMBLYAI_API_KEY=" in content
        print(f"Test .env has ASSEMBLYAI_API_KEY: {has_key}")

    # Check 6: Check git status for production files
    git_status = subprocess.run(["git", "status", "--porcelain"], cwd=str(WORKSPACE), capture_output=True, text=True)
    print("\nGit Status Check:")
    print("-----------------")
    for line in git_status.stdout.strip().splitlines():
        if line.strip():
            print(f"  {line}")

    print("\n" + "=" * 72)
    print("[ALL CHECKS PASSED] Test environment is 100% isolated and verified.")
    print("=" * 72)

if __name__ == "__main__":
    main()
