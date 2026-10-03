import csv
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
print('total:', len(rows)-1)
print('Last 30 rows:')
for r in rows[-30:]:
    if len(r) > 33:
        notes = r[33] if len(r) > 33 else ''
        name = r[1][:45]
        url = r[3][:50]
        lat, lon = r[24], r[25]
        city = r[21]
        country = r[19]
        print(f'  [{r[0]}] {name:<45} | {url}')
        print(f'    ({lat}, {lon}) | {city}, {country}')
