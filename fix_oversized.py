"""fix_oversized.py — Find rows that have too many cols (unclosed quotes/commas) and trim.

The most common cause: free-text description field has an unescaped comma that splits into multiple cols.
We need to find such rows, join extra cols back into the description, and rewrite.
"""
import csv
import os
import re

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
EXPECTED_LEN = 35

with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
header = rows[0]

fixed = 0
new_rows = [header]
for r in rows[1:]:
    if len(r) == EXPECTED_LEN:
        new_rows.append(r)
        continue
    if len(r) > EXPECTED_LEN:
        # Likely description has unescaped commas
        # Strategy: find which col has too many entries, join back
        # Most often it's the description field (col 14) that overflows
        # If r[14] looks like start of description and r[15] looks like start of category,
        # join everything from 14 onward back together
        # Simple heuristic: if there are too many cols, the issue is in one specific field
        # Try to find the "break point" — the position where the next col looks wrong
        # Heuristic: col 14 should be description (starts with **cam view**)
        # col 15 should be category (should be 'public' or 'private')
        # Find first col that looks like category
        bp = None
        for i in range(14, len(r) - (EXPECTED_LEN - 16)):
            if r[i] in ('public', 'private', 'commercial', 'security', 'rural', 'urban', 'beach', 'tourism', 'campus'):
                bp = i
                break
        if bp is None:
            # Can't fix automatically, just truncate
            new_rows.append(r[:EXPECTED_LEN])
        else:
            # Join all overflow into col 14 (description)
            # Overflow is cols 14 through bp-1, joined back into col 14
            merged_desc = ','.join(r[14:bp])
            new_r = r[:14] + [merged_desc] + r[bp:]
            new_r = new_r[:EXPECTED_LEN]
            new_rows.append(new_r)
            fixed += 1
    elif len(r) < EXPECTED_LEN:
        # Pad with empty
        new_rows.append(r + [''] * (EXPECTED_LEN - len(r)))
    else:
        new_rows.append(r)

print(f'fixed {fixed} rows with too many cols')

tmp = CSV_PATH + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    for r in new_rows:
        w.writerow(r)
os.replace(tmp, CSV_PATH)
print(f'done, total rows: {len(new_rows)-1}')

# Verify
with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
    rows2 = list(csv.reader(f))
bad = sum(1 for r in rows2[1:] if len(r) != EXPECTED_LEN)
print(f'rows still with wrong col count: {bad}')
