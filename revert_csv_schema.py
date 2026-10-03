"""
Revert CSV schema change: keep only 2 new columns (road, location_precision).
The street/via info will go into the existing 'address' column via enrichment.
"""
import csv
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

# Read CSV
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

print(f"Current columns: {len(header)}")
print(f"Header: {header}")

# Remove the 'via' column we added
if 'via' in header:
    via_idx = header.index('via')
    print(f"Removing 'via' at index {via_idx}")
    header.pop(via_idx)
    for row in rows:
        if len(row) > via_idx:
            row.pop(via_idx)

# Find address index
addr_idx = header.index('address')
print(f"'address' is now at index {addr_idx}")

# Find precision index
if 'location_precision' in header:
    prec_idx = header.index('location_precision')
    print(f"'location_precision' is at index {prec_idx}")

print(f"Final columns: {len(header)}")
print(f"Header: {header}")

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)

print(f"\nWrote {len(rows)} rows with {len(header)} columns")
