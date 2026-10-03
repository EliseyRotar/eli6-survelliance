"""Remove exact duplicate rows from CSV (same idx + same content)."""
import csv
from pathlib import Path

CSV = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

with open(CSV, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
print(f'Before: {len(rows):,} rows')

# Use idx as primary key, keep first occurrence
seen = set()
unique = []
for row in rows:
    if len(row) != len(header):
        continue
    idx = row[0]
    key = (idx, tuple(row))
    if idx in seen:
        continue
    seen.add(idx)
    unique.append(row)

print(f'After: {len(unique):,} rows')
print(f'Removed: {len(rows) - len(unique):,} rows')

# Re-number idx to be unique (already unique from seen set, but might have gaps)
# Actually since we kept first occurrence, idx might still be duplicated in seen (if there are different content with same idx)
# Let's also dedup by idx keeping the first
idx_seen = set()
final = []
for row in unique:
    if row[0] in idx_seen:
        continue
    idx_seen.add(row[0])
    final.append(row)

print(f'Final: {len(final):,} rows (idx-unique)')
print(f'Removed by idx dup: {len(unique) - len(final):,}')

with open(CSV, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for r in final:
        writer.writerow(r)
print('Saved.')
