import csv
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))

total = len(rows) - 1
has_lat = sum(1 for r in rows[1:] if len(r) > 23 and r[23].strip() and r[23].strip() != '0.0')
has_country = sum(1 for r in rows[1:] if len(r) > 19 and r[19].strip())
print(f'total: {total}')
print(f'has_lat: {has_lat} ({has_lat/total*100:.1f}%)')
print(f'has_country: {has_country} ({has_country/total*100:.1f}%)')

sources = {}
for r in rows[1:]:
    if len(r) <= 31:
        continue
    notes = r[31]
    if 'source=' in notes:
        s = notes.split('source=')[1].split(',')[0].split(';')[0]
    else:
        s = '?'
    sources.setdefault(s, {'total':0, 'lat':0, 'country':0})
    sources[s]['total'] += 1
    if len(r) > 23 and r[23].strip():
        sources[s]['lat'] += 1
    if len(r) > 19 and r[19].strip():
        sources[s]['country'] += 1
print('By source:')
for s, st in sorted(sources.items(), key=lambda x: -x[1]['total'])[:15]:
    pct_lat = st['lat']/st['total']*100 if st['total'] else 0
    pct_cty = st['country']/st['total']*100 if st['total'] else 0
    print(f'  {s}: {st["lat"]}/{st["total"]} lat ({pct_lat:.1f}%), {st["country"]}/{st["total"]} country ({pct_cty:.1f}%)')
