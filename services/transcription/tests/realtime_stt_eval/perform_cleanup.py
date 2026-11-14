import os
import sys
import shutil
import json
from pathlib import Path

workspace = Path(r"A:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab")
home = Path.home()
moss_hf = home / ".cache" / "huggingface" / "hub" / "models--OpenMOSS-Team--MOSS-Transcribe-Diarize"

targets_to_delete = [
    ("tests/moss_env", workspace / "tests" / "moss_env"),
    ("tests/moss_hybrid", workspace / "tests" / "moss_hybrid"),
    ("tests/moss_profile_env", workspace / "tests" / "moss_profile_env"),
    ("tests/moss_profile_env_clean", workspace / "tests" / "moss_profile_env_clean"),
    ("tests/moss_realtime", workspace / "tests" / "moss_realtime"),
    ("tests/moss_test", workspace / "tests" / "moss_test"),
    ("HuggingFace MOSS Cache", moss_hf),
]

def on_rm_error(func, path, exc_info):
    """Handle readonly or permission issues on Windows during removal."""
    try:
        os.chmod(path, 0o777)
        func(path)
    except Exception as e:
        print(f"  [WARN] Failed to delete {path}: {e}")

print("=" * 70)
print("PHASE 1: EXECUTING TARGETED MOSS CLEANUP")
print("=" * 70)

deleted_records = []
total_reclaimed_bytes = 0

# Load before inventory
inv_file = workspace / "tests" / "realtime_stt_eval" / "inventory_before.json"
before_inv = {}
if inv_file.exists():
    try:
        data = json.loads(inv_file.read_text(encoding="utf-8"))
        for item in data.get("targets", []):
            before_inv[item["label"]] = item
    except Exception:
        pass

for label, p in targets_to_delete:
    print(f"\nProcessing: {label} ({p})")
    if not p.exists():
        print(f"  -> Path does not exist. Skipping.")
        continue

    item_before = before_inv.get(label, {})
    bytes_est = item_before.get("bytes", 0)
    mb_est = item_before.get("mb", 0)
    gb_est = item_before.get("gb", 0)

    try:
        if p.is_dir():
            shutil.rmtree(p, onerror=on_rm_error)
        else:
            p.unlink()

        # Verify removal
        if not p.exists():
            print(f"  -> SUCCESSFULLY DELETED! Reclaimed approx {mb_est:.2f} MB ({gb_est:.3f} GB)")
            total_reclaimed_bytes += bytes_est
            deleted_records.append({
                "label": label,
                "path": str(p),
                "deleted": True,
                "bytes_reclaimed": bytes_est,
                "mb_reclaimed": mb_est,
                "gb_reclaimed": gb_est
            })
        else:
            print(f"  -> [ERROR] Path still exists after deletion attempt!")
            deleted_records.append({
                "label": label,
                "path": str(p),
                "deleted": False,
                "bytes_reclaimed": 0,
                "mb_reclaimed": 0,
                "gb_reclaimed": 0
            })
    except Exception as ex:
        print(f"  -> [EXCEPTION] {ex}")

print("\n" + "=" * 70)
print(f"CLEANUP SUMMARY: Reclaimed {total_reclaimed_bytes / (1024*1024*1024):.3f} GB ({total_reclaimed_bytes / (1024*1024):.2f} MB)")
print("=" * 70)

# Save result json
out_json = workspace / "tests" / "realtime_stt_eval" / "inventory_after.json"
out_json.write_text(json.dumps({
    "deleted_records": deleted_records,
    "total_reclaimed_bytes": total_reclaimed_bytes,
    "total_reclaimed_mb": round(total_reclaimed_bytes / (1024*1024), 2),
    "total_reclaimed_gb": round(total_reclaimed_bytes / (1024*1024*1024), 3)
}, indent=2), encoding="utf-8")
print(f"Saved results to {out_json}")
