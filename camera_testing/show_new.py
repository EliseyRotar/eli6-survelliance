import csv, sys
io = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\new_cams_summary.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.reader(f))
for r in rows[1:]:
    idx = r[0]
    name = r[1]
    url = r[2]
    live = r[3]
    country = r[19]
    region = r[20]
    city = r[21]
    org = r[26]
    notes = r[30] if len(r) > 30 else ''
    print(f'{idx} | {city:25s} {country:15s} | {live[:90]}', file=io)
io.close()
