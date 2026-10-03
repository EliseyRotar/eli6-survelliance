import csv
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
print(f'total before: {len(rows)-1}')
last = rows[-1]
print(f'last row len: {len(last)}')
print(f'last row idx: {last[0]}, url: {last[3][:50]}')
if 'test-fix' in last[33] if len(last) > 33 else '':
    rows = rows[:-1]
    import os
    tmp = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow(r)
    os.replace(tmp, r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
    print(f'removed test row, total now: {len(rows)-1}')
else:
    # Last 3 rows
    print('Last 3 rows:')
    for r in rows[-3:]:
        print(f'  [{r[0]}] len={len(r)} | {r[3][:50]}')
