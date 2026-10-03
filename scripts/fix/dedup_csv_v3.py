"""Remove rows with non-digit idx from CSV."""
import csv
from pathlib import Path

CSV = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

with open(CSV, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
print(f'Before: {len(rows):,} rows')

valid = []
removed = 0
for row in rows:
    if len(row) == len(header) and row[0].isdigit():
        valid.append(row)
    else:
        removed += 1

print(f'After: {len(valid):,} rows (removed {removed})')

with open(CSV, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for r in valid:
        writer.writerow(r)
print('Saved.')
