"""
Restore the CSV from the pre-session-27 backup, then redo the ingestion
with the correct 37-column format.

Steps:
1. Copy CSV from backup
2. Re-run session27_ingest.py (with fixed column counts)
3. Re-run session27_opencctv_ingest.py (with fixed column counts)
"""
import shutil
import subprocess
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
BACKUP_CSV = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\backups\backup_20260912_000521\controllable_Webcams.csv')

# Verify backup exists
if not BACKUP_CSV.exists():
    print(f"ERROR: Backup not found at {BACKUP_CSV}")
    exit(1)

# Get current row count
import csv
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    current_rows = sum(1 for _ in f) - 1  # minus header
print(f"Current rows: {current_rows}")

# Get backup row count
with open(BACKUP_CSV, encoding='utf-8', newline='') as f:
    backup_rows = sum(1 for _ in f) - 1
print(f"Backup rows: {backup_rows}")

# Restore
print(f"Restoring from {BACKUP_CSV}...")
shutil.copy2(BACKUP_CSV, CSV_PATH)
print("Restored!")

# Verify
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    restored = sum(1 for _ in f) - 1
print(f"After restore: {restored} rows")
