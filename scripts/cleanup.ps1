# Clinical Scribe Platform - Safe Cleanup Script
# Cleans temporary files, test output, and pycache WITHOUT removing database volumes or persistent stores.

Write-Host "Cleaning up test outputs and Python caches..." -ForegroundColor Yellow

# Remove pytest cache
Get-ChildItem -Path . -Filter ".pytest_cache" -Directory -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Remove pycache
Get-ChildItem -Path . -Filter "__pycache__" -Directory -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Clean test audio session outputs but keep directory
if (Test-Path "output") {
    Get-ChildItem -Path "output" -Filter "session_test*.json" | Remove-Item -Force -ErrorAction SilentlyContinue
}

Write-Host "[OK] Cleaned temporary caches. Persistent databases and configuration preserved." -ForegroundColor Green
