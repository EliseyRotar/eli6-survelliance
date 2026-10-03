import csv
csv.field_size_limit(2**31 - 1)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv','r',encoding='utf-8',errors='replace') as f:
    rows = list(csv.reader(f))
# Show rows around 67000
for i in range(67000, min(67020, len(rows))):
    r = rows[i]
    print(f'[{i}] len={len(r)} idx={r[0] if r else "?"} name={r[1][:30] if len(r)>1 else "?"} url={r[3][:50] if len(r)>3 else "?"} notes={(r[33][:80] if len(r)>33 else "")[:80]}')
