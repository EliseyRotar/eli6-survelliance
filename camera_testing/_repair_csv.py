"""Repair CSV by removing broken short rows.

Strategy: load all rows, filter to those with len==35, save back.
"""
import csv
import os
import sys

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
BACKUP_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\backups\controllable_Webcams_pre_repair.csv'

csv.field_size_limit(2**31 - 1)

with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    rows = list(csv.reader(f))

print('total rows:', len(rows))
header = rows[0]
print('header cols:', len(header))

bad = []
good = []
for i, r in enumerate(rows[1:], 1):
    if len(r) == 35:
        good.append(r)
    else:
        bad.append((i, len(r), r[:3]))
        print(f'  bad row {i}: len={len(r)}, preview={r[:3]}')

print(f'good: {len(good)}, bad: {len(bad)}')

# Backup
os.makedirs(os.path.dirname(BACKUP_PATH), exist_ok=True)
with open(BACKUP_PATH, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    w.writerow(header)
    for r in rows[1:]:
        w.writerow(r)
print(f'backed up to {BACKUP_PATH}')

# Save fixed
tmp = CSV_PATH + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    w.writerow(header)
    for r in good:
        w.writerow(r)

import os as _os
for _ in range(10):
    try:
        _os.replace(tmp, CSV_PATH)
        break
    except PermissionError:
        import time; time.sleep(0.5)

print(f'fixed CSV: {len(good)+1} rows')
