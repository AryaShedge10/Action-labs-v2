import os
import sys
import json
import subprocess
from pathlib import Path

def get_dir_size(path_str):
    p = Path(path_str)
    if not p.exists():
        return 0, 0
    total_bytes = 0
    file_count = 0
    for root, dirs, files in os.walk(p):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_bytes += os.path.getsize(fp)
                file_count += 1
            except Exception:
                pass
    return total_bytes, file_count

home = Path.home()
hf_cache = home / ".cache" / "huggingface" / "hub"
moss_hf = hf_cache / "models--OpenMOSS-Team--MOSS-Transcribe-Diarize"

workspace = Path(r"A:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab")

targets = [
    ("tests/moss_env", workspace / "tests" / "moss_env"),
    ("tests/moss_hybrid", workspace / "tests" / "moss_hybrid"),
    ("tests/moss_profile_env", workspace / "tests" / "moss_profile_env"),
    ("tests/moss_profile_env_clean", workspace / "tests" / "moss_profile_env_clean"),
    ("tests/moss_realtime", workspace / "tests" / "moss_realtime"),
    ("tests/moss_test", workspace / "tests" / "moss_test"),
    ("HuggingFace MOSS Cache", moss_hf),
]

results = []
grand_total_bytes = 0

print("=" * 70)
print("PHASE 0 INVENTORY: MOSS ARTIFACTS & DISK USAGE")
print("=" * 70)

for label, p in targets:
    b, count = get_dir_size(p)
    mb = b / (1024 * 1024)
    gb = b / (1024 * 1024 * 1024)
    grand_total_bytes += b
    results.append({
        "label": label,
        "path": str(p),
        "exists": p.exists(),
        "bytes": b,
        "mb": round(mb, 2),
        "gb": round(gb, 3),
        "file_count": count
    })
    status = f"{mb:.2f} MB ({gb:.3f} GB) across {count} files" if p.exists() else "DOES NOT EXIST"
    print(f"[{'FOUND' if p.exists() else 'MISSING'}] {label} -> {status}")

print("-" * 70)
print(f"GRAND TOTAL MOSS DISK USAGE: {grand_total_bytes / (1024*1024*1024):.3f} GB ({grand_total_bytes / (1024*1024):.2f} MB)")
print("=" * 70)

# Check Git Status
git_res = subprocess.run(["git", "status", "--short"], cwd=str(workspace), capture_output=True, text=True)
print("\nGIT STATUS SUMMARY:")
print(git_res.stdout)

# Check Production venv & Backend
prod_venv = workspace / "venv"
prod_backend = workspace / "app"
prod_frontend = workspace / "static"

print("\nPRODUCTION COMPONENTS IDENTIFIED:")
print(f"  Backend: {prod_backend} (exists: {prod_backend.exists()})")
print(f"  Frontend: {prod_frontend} (exists: {prod_frontend.exists()})")
print(f"  Venv: {prod_venv} (exists: {prod_venv.exists()})")

# Write inventory json
out_json = workspace / "tests" / "realtime_stt_eval" / "inventory_before.json"
out_json.write_text(json.dumps({
    "targets": results,
    "grand_total_bytes": grand_total_bytes,
    "grand_total_mb": round(grand_total_bytes / (1024*1024), 2),
    "grand_total_gb": round(grand_total_bytes / (1024*1024*1024), 3),
    "git_status": git_res.stdout
}, indent=2), encoding="utf-8")
print(f"\nSaved inventory to {out_json}")
