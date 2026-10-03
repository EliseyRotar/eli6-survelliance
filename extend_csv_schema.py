"""
Extend CSV schema with new columns: via, road, location_precision
- via: street/road name (from reverse geocoding)
- road: highway/route identifier (e.g. "I-5", "A-6", "Hwy 99")
- location_precision: precise/approximate/city/region/host_default

Insert these 3 columns after 'address' (position 24).
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

# Find the 'address' column index
addr_idx = header.index('address')
print(f"'address' is at index {addr_idx}")

# New columns to insert AFTER 'address' (at index addr_idx+1, +2, +3)
new_cols = ['via', 'road', 'location_precision']

# Build new header: insert new_cols after 'address'
new_header = header[:addr_idx+1] + new_cols + header[addr_idx+1:]
print(f"New header ({len(new_header)} cols): {new_header}")

# For each data row, insert empty strings for the 3 new columns
new_rows = []
for row in rows:
    if not row or len(row) < len(header):
        # Skip malformed or empty
        new_rows.append(row)
        continue
    new_row = row[:addr_idx+1] + ['', '', ''] + row[addr_idx+1:]
    new_rows.append(new_row)

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(new_header)
    for row in new_rows:
        writer.writerow(row)

print(f"\nWrote {len(new_rows)} rows with new {len(new_cols)} columns")
print(f"Total columns now: {len(new_header)}")
