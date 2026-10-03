"""fix_shifted_v2.py — Detect and fix rows where lat/lon fell into wrong columns.

Detect pattern:
- col 23 (address) contains a number (looks like lat)
- col 24 (lat) contains a number (looks like lon)
- col 25 (lon) contains text (org/isp)
- col 26 (geo_source) contains text

Shift back:
- new col 23 (address) = old col 25 (text -> empty for lost address)
- new col 24 (lat) = old col 23
- new col 25 (lon) = old col 24
- new col 26 (geo_source) = empty
- new col 27-34 = old col 26-33
"""
import csv
import os
import re

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
header = rows[0]

fixed = 0
new_rows = [header]
for r in rows[1:]:
    if len(r) < len(header):
        r = r + [''] * (len(header) - len(r))
    elif len(r) > len(header):
        r = r[:len(header)]
    # Detect shift: col 23 = numeric (should be text), col 24 = numeric, col 25 = text
    is_shift = False
    if re.match(r'^-?\d+\.?\d*$', r[23].strip()) and re.match(r'^-?\d+\.?\d*$', r[24].strip()):
        if r[25] and not re.match(r'^-?\d+\.?\d*$', r[25].strip()):
            is_shift = True

    if is_shift:
        # Save the lat/lon values from cols 23, 24
        real_lat = r[23]
        real_lon = r[24]
        # Save other fields
        other = r[26:33] if len(r) >= 33 else []
        # Rebuild row
        new_r = list(r[:23])  # idx through zip (cols 0-22)
        new_r.append('')  # 23 = address (lost)
        new_r.append(real_lat)  # 24 = lat
        new_r.append(real_lon)  # 25 = lon
        new_r.append('')  # 26 = geo_source (lost)
        # 27-33 = original cols 26-32
        for i in range(27, 34):
            if i-1 < len(r):
                new_r.append(r[i-1])
            else:
                new_r.append('')
        # 34 = csv_id (lost)
        new_r.append('')
        new_rows.append(new_r)
        fixed += 1
    else:
        new_rows.append(r)

print(f'fixed {fixed} shifted rows')

tmp = CSV_PATH + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    for r in new_rows:
        w.writerow(r)
os.replace(tmp, CSV_PATH)
print('done')
