"""
Fix ALL 22,544 bad rows from session27 ingestion.
The 35-col rows were APPENDED to a 37-col CSV header, so they ended up
shifted +2 in their final positions. The data is preserved but at wrong columns.

Strategy: For each bad row (idx in our range), shift values at positions 25-34
to positions 27-36, with empty values at positions 25,26 (road, location_precision).

NOTE: only my 22,544 rows need this (idx 212146+). Earlier rows are good.
"""
import csv
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

# Read all
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

# My rows start at idx 212146. Before that, all rows are good.
BAD_START_IDX = 212146

fixed = 0
for row in rows:
    try:
        idx = int(row[0]) if row[0].isdigit() else 0
    except:
        idx = 0
    if idx < BAD_START_IDX:
        continue
    # Pad to 37 first
    while len(row) < 37:
        row.append('')
    # Now extract: values at positions 25..34 should go to 27..36
    # Save: row[0..24] (untouched), row[25..34] (shifted by +2)
    head = row[:25]  # 0..24 inclusive
    tail = row[25:35]  # 25..34 inclusive (10 values)
    # Reassemble: head[0..24] + ['', ''] + tail[0..10]
    new_row = head + ['', ''] + tail + row[35:]  # row[35:37] should be empty for original bad rows
    # Trim/pad to exactly 37
    new_row = new_row[:37]
    while len(new_row) < 37:
        new_row.append('')
    # Replace in-place
    row.clear()
    row.extend(new_row)
    fixed += 1

print(f'Fixed {fixed} rows')

# Verify a sample
for r in rows:
    if r[0] == '212180':  # AZ511 cam 635
        print(f'\nSample fixed AZ511 row (212180):')
        for i, (k, v) in enumerate(zip(header, r)):
            if v:
                print(f'  [{i:2d}] {k} = {v[:60]}')
        break
for r in rows:
    if r[0] == '214000':  # NY511 sample
        if r[0] == '214000':
            print(f'\nSample fixed NY511 row (214000):')
            for i, (k, v) in enumerate(zip(header, r)):
                if v:
                    print(f'  [{i:2d}] {k} = {v[:60]}')
            break
for r in rows:
    if r[0] == '220000':  # OpenCCTV
        print(f'\nSample fixed OpenCCTV row (220000):')
        for i, (k, v) in enumerate(zip(header, r)):
            if v:
                print(f'  [{i:2d}] {k} = {v[:60]}')
        break

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
print(f'\nWrote {len(rows)} rows')
