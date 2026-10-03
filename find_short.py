import csv
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
short = [(i, r) for i, r in enumerate(rows) if len(r) != 35]
print(f'rows with !=35 cols: {len(short)}')
for i, r in short:
    print(f'  idx={r[0] if len(r) > 0 else "?"} len={len(r)} | {r[1][:40] if len(r) > 1 else ""} | {r[3][:50] if len(r) > 3 else ""}')
