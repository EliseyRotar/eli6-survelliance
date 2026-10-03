import csv
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))

# Show header
print('Header len:', len(rows[0]))
print('Header:', rows[0])

# Find first row with len 33 vs 35
short_idx = None
for i, r in enumerate(rows):
    if len(r) < 34:
        short_idx = i
        break
print(f'\nFirst short row at idx: {short_idx+1 if short_idx else "none"}')
if short_idx:
    r = rows[short_idx]
    print(f'Row content (header has 35 cols, row has {len(r)}):')
    for j in [0, 1, 2, 3, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34]:
        if j < len(r):
            print(f'  [{j}] {rows[0][j] if j < len(rows[0]) else "<header-overflow>"}: {r[j][:60]}')
        else:
            print(f'  [{j}] {rows[0][j] if j < len(rows[0]) else "<header-overflow>"}: <MISSING>')

# Count total short rows
short_total = sum(1 for r in rows[1:] if len(r) < 34)
print(f'\nTotal rows: {len(rows)-1}')
print(f'Short rows (len < 34): {short_total}')
