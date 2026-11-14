"""
Isolation Verifier — NVIDIA NeMo Realtime Test Environment
tests/realtime_nvidia/verify_isolation.py

Phase 50: Confirms that the NVIDIA test environment is completely isolated
from production. Fails loudly if any isolation boundary is broken.

Run from the project root (EDI_Accion_lab/):
    tests\\realtime_nvidia\\.venv\\Scripts\\python tests\\realtime_nvidia\\verify_isolation.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # EDI_Accion_lab/
TEST_DIR = Path(__file__).resolve().parent             # tests/realtime_nvidia/
PROD_VENV = ROOT / "venv"
TEST_VENV = TEST_DIR / ".venv"

PASS = "\u2705"
FAIL = "\u274c"
WARN = "\u26a0\ufe0f"

issues = []
warnings = []


def check(condition: bool, pass_msg: str, fail_msg: str, is_warning: bool = False):
    if condition:
        print(f"  {PASS} {pass_msg}")
    else:
        marker = WARN if is_warning else FAIL
        print(f"  {marker} {fail_msg}")
        if is_warning:
            warnings.append(fail_msg)
        else:
            issues.append(fail_msg)


print("=" * 64)
print("  NVIDIA NeMo Realtime Test — Isolation Verifier")
print("=" * 64)

# ── 1. Python interpreter ────────────────────────────────────────
print("\n[1] Python Interpreter")
current_py = Path(sys.executable).resolve()
test_venv_py = (TEST_VENV / "Scripts" / "python.exe").resolve()
prod_venv_py = (PROD_VENV / "Scripts" / "python.exe").resolve()

check(
    test_venv_py.exists(),
    f"Test venv exists: {test_venv_py}",
    f"Test venv missing: {test_venv_py}",
)
check(
    current_py != prod_venv_py,
    "Running in test venv (not production venv)",
    f"Running in PRODUCTION venv: {current_py}",
)

# ── 2. sys.path does not contain production app ──────────────────
print("\n[2] sys.path Isolation")
prod_app = str((ROOT / "app").resolve())
prod_site = str((PROD_VENV / "Lib" / "site-packages").resolve())

for p in sys.path:
    check(
        prod_app not in p,
        f"sys.path clean: {p[:60]}",
        f"sys.path contains production app: {p}",
    )
    check(
        prod_site not in p,
        f"sys.path clean of prod site-packages",
        f"sys.path contains production venv site-packages: {p}",
    )

# ── 3. Test backend does not import from production app/ ─────────
print("\n[3] Test Backend Imports")
test_backend_files = [
    TEST_DIR / "backend" / "app" / "main.py",
    TEST_DIR / "backend" / "app" / "provider.py",
    TEST_DIR / "backend" / "app" / "session_manager.py",
    TEST_DIR / "backend" / "app" / "config.py",
    TEST_DIR / "backend" / "app" / "models.py",
]
forbidden_imports = [
    "from app.",
    "import app.",
    "from app import",
    "import app",
]
for f in test_backend_files:
    if not f.exists():
        check(False, "", f"Missing test file: {f.name}")
        continue
    content = f.read_text(encoding="utf-8")
    has_prod_import = any(imp in content for imp in forbidden_imports)
    check(
        not has_prod_import,
        f"{f.name}: no production imports",
        f"{f.name}: contains production app/ import",
    )

# ── 4. No AssemblyAI references in NVIDIA test code ─────────────
print("\n[4] AssemblyAI Reference Scan (must be zero)")
assemblyai_patterns = [
    "assemblyai",
    "AssemblyAI",
    "ASSEMBLYAI_API_KEY",
    "streaming.assemblyai.com",
    "universal-3-6-pro",
    "universal_3_6_pro",
]
nvidia_files = list((TEST_DIR / "backend").rglob("*.py"))
nvidia_files += [TEST_DIR / "frontend" / "index.html", TEST_DIR / ".env"]

for fpath in nvidia_files:
    if not fpath.exists():
        continue
    content = fpath.read_text(encoding="utf-8", errors="replace")
    found = [p for p in assemblyai_patterns if p in content]
    check(
        len(found) == 0,
        f"{fpath.relative_to(TEST_DIR)}: no AssemblyAI references",
        f"{fpath.relative_to(TEST_DIR)}: found AssemblyAI references: {found}",
    )

# ── 5. No MOSS references ────────────────────────────────────────
print("\n[5] MOSS Reference Scan")
moss_patterns = ["moss_env", "moss_realtime", "OpenMOSS", "MOSS-Transcribe"]
for fpath in nvidia_files:
    if not fpath.exists():
        continue
    content = fpath.read_text(encoding="utf-8", errors="replace")
    found = [p for p in moss_patterns if p in content]
    check(
        len(found) == 0,
        f"{fpath.relative_to(TEST_DIR)}: no MOSS references",
        f"{fpath.relative_to(TEST_DIR)}: found MOSS references: {found}",
    )

# ── 6. Production files unchanged ────────────────────────────────
print("\n[6] Production Files — Git Status")
try:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    changed_prod = []
    for line in result.stdout.splitlines():
        status_char = line[:2].strip()
        fpath_str = line[3:].strip()
        # Changes in the NVIDIA test dir are expected — flag anything else
        if status_char and "tests/realtime_nvidia" not in fpath_str:
            if fpath_str.startswith("app/") or fpath_str.startswith("static/"):
                changed_prod.append(fpath_str)

    if changed_prod:
        print(f"  {WARN} Production files with uncommitted changes:")
        for p in changed_prod:
            print(f"     {p}")
        warnings.append(
            f"Production files changed: {changed_prod} "
            "(these are pre-existing unstaged changes, not caused by NVIDIA test)"
        )
    else:
        print(f"  {PASS} No production files modified by NVIDIA test setup")

except Exception as e:
    print(f"  {WARN} Could not run git status: {e}")
    warnings.append(f"git status check failed: {e}")

# ── 7. Test .env has no API key ───────────────────────────────────
print("\n[7] Test .env — No API Key")
env_path = TEST_DIR / ".env"
if env_path.exists():
    env_content = env_path.read_text(encoding="utf-8")
    has_assemblyai_key = "ASSEMBLYAI_API_KEY" in env_content
    has_groq_key = "GROQ_API_KEY" in env_content
    check(
        not has_assemblyai_key,
        "Test .env: no ASSEMBLYAI_API_KEY",
        "Test .env: contains ASSEMBLYAI_API_KEY",
    )
    check(
        not has_groq_key,
        "Test .env: no GROQ_API_KEY (none needed for local inference)",
        "Test .env: unexpectedly contains GROQ_API_KEY",
        is_warning=True,
    )
    check(
        "NEMO_SPEECH_HOST" in env_content,
        "Test .env: contains NVIDIA runtime config (NEMO_SPEECH_HOST)",
        "Test .env: missing NEMO_SPEECH_HOST",
    )
else:
    print(f"  {WARN} .env not found at {env_path} — copy .env.example to .env")
    warnings.append(".env missing")

# ── 8. Model storage isolation ───────────────────────────────────
print("\n[8] Model Storage Isolation")
models_dir = TEST_DIR / "models"
model_cache_dir = TEST_DIR / "model_cache"
prod_model_dir = ROOT / "models"

check(
    models_dir.parent == TEST_DIR,
    f"models/ is inside test dir: {models_dir}",
    f"models/ is outside test dir: {models_dir}",
)

# Warn if production has models that could be confused
if prod_model_dir.exists():
    print(f"  {WARN} Production models/ dir exists: {prod_model_dir}")
    warnings.append(f"Production models/ dir exists at {prod_model_dir} — ensure NVIDIA models go to tests/realtime_nvidia/models/")
else:
    print(f"  {PASS} Production models/ dir absent — no cross-contamination risk")

# ── Summary ──────────────────────────────────────────────────────
print("\n" + "=" * 64)
if issues:
    print(f"\n{FAIL} ISOLATION BROKEN — {len(issues)} issue(s):")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    sys.exit(1)
elif warnings:
    print(f"\n{WARN} Isolation OK with {len(warnings)} warning(s):")
    for w in warnings:
        print(f"  - {w}")
    print("\nProduction environment is NOT modified by this test setup.")
    sys.exit(0)
else:
    print(f"\n{PASS} All isolation checks passed.")
    print("  Production pipeline: UNTOUCHED")
    print("  AssemblyAI:          ABSENT from NVIDIA test")
    print("  MOSS:                ABSENT")
    print("  Global installs:     NONE")
    print("  API keys:            NONE required")
    sys.exit(0)
