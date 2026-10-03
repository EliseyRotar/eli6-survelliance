import csv, re
csv.field_size_limit(2**31 - 1)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv','r',encoding='utf-8',errors='replace') as f:
    rows = list(csv.reader(f))
print('total rows:', len(rows))
# Show last 50 rows
for i in range(max(0, len(rows)-50), len(rows)):
    r = rows[i]
    nm = r[1][:30] if len(r) > 1 else ''
    url = r[3][:50] if len(r) > 3 else ''
    notes = r[33][:50] if len(r) > 33 else ''
    print(f'[{i}] idx={r[0]:>5} name={nm} url={url} notes={notes}')
