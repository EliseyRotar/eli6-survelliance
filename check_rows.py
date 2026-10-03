import csv
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
header = rows[0]
print('header len:', len(header))
short = 0
long = 0
for r in rows[1:]:
    if len(r) < len(header):
        short += 1
    elif len(r) > len(header):
        long += 1
print(f'short: {short}, long: {long}')
# Sample a short row
for r in rows[1:]:
    if len(r) < len(header):
        print('short sample:')
        for j, h in enumerate(header):
            v = r[j][:50] if j < len(r) else '<missing>'
            print(f'  [{j}] {h}: {v}')
        break
