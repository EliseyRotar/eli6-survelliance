import csv
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
header = rows[0]
fixed = 0
new_rows = [header]
for r in rows[1:]:
    if len(r) < len(header):
        r = r + [''] * (len(header) - len(r))
        fixed += 1
    elif len(r) > len(header):
        r = r[:len(header)]
    new_rows.append(r)
print(f'padded {fixed} short rows')
import os
tmp = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    for r in new_rows:
        w.writerow(r)
os.replace(tmp, r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
print(f'final total: {len(new_rows)-1}')
short = [i for i, r in enumerate(new_rows[1:]) if len(r) < len(header)]
print(f'short rows remaining: {len(short)}')
