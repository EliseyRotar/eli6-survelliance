import csv
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
short_idx = []
for i, r in enumerate(rows):
    if len(r) < 35:
        short_idx.append(i+1)
print(f'short rows: {len(short_idx)}')
print(f'first 5 short row idxs: {short_idx[:5]}')
for idx in short_idx[:5]:
    r = rows[idx-1]
    notes = r[33] if len(r) > 33 else '<missing>'
    print(f'\nRow {idx} (len={len(r)}):')
    print(f'  url: {r[3][:50]}')
    print(f'  notes: {notes[:80]}')
