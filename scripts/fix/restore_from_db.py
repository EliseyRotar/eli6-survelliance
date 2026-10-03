"""Restore master CSV from webcams.db SQLite backup.

Converts the 175,057-row webcams.db into the master CSV format.
This recovers the data lost in the PC crash.
"""
import os
import csv
import sqlite3
import time
import shutil

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
DB_PATH = os.path.join(WORKDIR, "camera_testing", "webcams.db")
CSV_PATH = os.path.join(WORKDIR, "controllable_Webcams.csv")
CSV_BAK = os.path.join(WORKDIR, "backups", "controllable_Webcams_pre_restore.csv")

print(f'[Restore] Reading {DB_PATH}')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Get row count
cur.execute("SELECT COUNT(*) FROM webcams")
count = cur.fetchone()[0]
print(f'  Rows: {count:,}')

# Get columns
cur.execute("PRAGMA table_info(webcams)")
cols_info = cur.fetchall()
columns = [c[1] for c in cols_info]
print(f'  Columns: {len(columns)} - {columns[:8]}...')

# Fetch all rows
print(f'  Fetching all rows...')
cur.execute("SELECT * FROM webcams ORDER BY idx")
rows = cur.fetchall()
print(f'  Got {len(rows):,} rows')

# First, back up the current (likely empty) CSV
if os.path.exists(CSV_PATH):
    shutil.copy(CSV_PATH, CSV_BAK)
    print(f'  Backed up current CSV to {CSV_BAK}')

# Now write to CSV atomically
tmp = CSV_PATH + ".tmp"
print(f'  Writing to {tmp}...')

with open(tmp, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)

# Atomic rename
os.replace(tmp, CSV_PATH)
print(f'  Renamed to {CSV_PATH}')

# Verify
size = os.path.getsize(CSV_PATH) / 1024 / 1024
print(f'  Final size: {size:.1f} MB')

# Read back to verify
csv.field_size_limit(2**31 - 1)
with open(CSV_PATH, 'r', encoding='utf-8') as f:
    csv_rows = list(csv.DictReader(f))
print(f'  Verified: {len(csv_rows):,} rows')

# Stats
ruse = [r for r in csv_rows if (r.get('project_name') or '') in ('ruse', 'ruse_v2', 'ruse_scan', 'ruse_ip_cam', 'ruse_isp_scan')]
print(f'  Ruse cams: {len(ruse)}')

from collections import Counter
brands = Counter(r.get('brand') or '' for r in csv_rows)
print(f'  Top brands:')
for b, c in brands.most_common(10):
    label = b if b else '<empty>'
    print(f'    {label}: {c:,}')

print(f'\n[Restore] COMPLETE!')
print(f'  CSV restored to {count:,} rows from webcams.db')
