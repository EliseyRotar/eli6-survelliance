"""Remove empty rows from CSV (rows where idx is empty)."""
import csv
import os

csv.field_size_limit(2**31 - 1)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
BACKUP_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\backups\controllable_Webcams_with_empty_rows.csv'

with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    rows = list(csv.reader(f))

print('total rows:', len(rows))
empty = 0
good = []
for r in rows[1:]:
    if len(r) < 35:
        empty += 1
        continue
    if not r[0] or not r[1]:
        empty += 1
        continue
    if not r[3]:
        # idx and name present but no URL = likely empty/duplicate
        # keep if has any source marker
        has_source = len(r) > 33 and r[33] and '_id=' in r[33]
        if not has_source:
            empty += 1
            continue
    good.append(r)

print(f'empty: {empty}, good: {len(good)}')

# Backup
os.makedirs(os.path.dirname(BACKUP_PATH), exist_ok=True)
with open(BACKUP_PATH, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    w.writerow(rows[0])
    for r in rows[1:]:
        w.writerow(r)
print(f'backed up')

# Save
tmp = CSV_PATH + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    w.writerow(rows[0])
    for r in good:
        w.writerow(r)

import os as _os
import time as _time
for _ in range(30):
    try:
        if _os.path.exists(tmp):
            _os.replace(tmp, CSV_PATH)
            break
        else:
            _time.sleep(0.5)
    except PermissionError:
        _time.sleep(0.5)
print(f'fixed CSV: {len(good)+1} rows')
