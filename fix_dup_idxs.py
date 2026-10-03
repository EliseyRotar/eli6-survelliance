"""
Fix duplicate idxs in CSV. The new opencctv rows used sequential idxs starting from
max+1, but some previous ingestion also used those idxs.
"""
import csv
from collections import Counter
from pathlib import Path

CSV = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

with open(CSV, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
H = {k: i for i, k in enumerate(header)}

# Find dup idxs and the new rows (those with opencctv_ingest_v2 in notes)
seen_idx = {}
new_rows_to_fix = []
for ri, row in enumerate(rows):
    if len(row) != len(header):
        continue
    idx = row[H['idx']]
    notes = row[H['notes']] if len(row) > H['notes'] else ''
    if not idx.isdigit():
        continue
    idx_int = int(idx)
    if idx in seen_idx:
        # Duplicate
        first_ri = seen_idx[idx]
        first_notes = rows[first_ri][H['notes']]
        # Keep the older one (no opencctv_ingest_v2), drop/renumber the new one
        if 'opencctv_ingest_v2' in notes and 'opencctv_ingest_v2' not in first_notes:
            new_rows_to_fix.append(ri)
        elif 'opencctv_ingest_v2' in first_notes and 'opencctv_ingest_v2' not in notes:
            new_rows_to_fix.append(first_ri)
            seen_idx[idx] = ri
        else:
            new_rows_to_fix.append(ri)
    else:
        seen_idx[idx] = ri

print(f'Rows to renumber: {len(new_rows_to_fix)}')

# Find max idx (excluding the dup rows)
max_idx = 0
for ri, row in enumerate(rows):
    if ri in new_rows_to_fix:
        continue
    if len(row) == len(header):
        idx = row[H['idx']]
        if idx.isdigit():
            max_idx = max(max_idx, int(idx))

print(f'Max idx (excl dups): {max_idx}')
next_idx = max_idx + 1

# Renumber
for ri in new_rows_to_fix:
    row = rows[ri]
    row[H['idx']] = str(next_idx)
    next_idx += 1

# Write back
with open(CSV, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for r in rows:
        writer.writerow(r)

# Verify
with open(CSV, encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    rows2 = list(reader)
idxs = [r['idx'] for r in rows2 if r['idx'].isdigit()]
c = Counter(idxs)
dups = {k: v for k, v in c.items() if v > 1}
print(f'After fix: {len(rows2)} rows, {len(dups)} dup idxs')
print(f'Max idx: {max(int(i) for i in idxs)}')
