import csv, re

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
rows = []
with open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        u = (r.get('live_stream_url') or '') + ' ' + (r.get('url') or '')
        if 'bizkaimove' in u.lower():
            rows.append(r)
print('bizkaimove rows total:', len(rows))
matched = [r for r in rows if re.search(r'(?i)[·�]\s*Bizkaimove\s*[·�]\s*#\d+', r['project_name'] or '')]
print('pattern-matched (renamed if catalog):', len(matched))
others = [r for r in rows if r not in matched]
print('NOT matching pattern:', len(others))
for r in others[:40]:
    print('   ', r['csv_id'], '|', repr(r['project_name'])[:90], '| fixed:', 'name-fixed' in (r['notes'] or ''))
print('--- sample renamed (have name-fixed note):')
n = 0
for r in rows:
    if 'name-fixed=euskadi-ods' in (r['notes'] or ''):
        n += 1
        if n <= 10:
            print('   ', r['csv_id'], '|', r['project_name'])
print('total renamed with note:', n)
# trafikoa spot check
t = 0
with open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if 'name-fixed=euskadi-ods' in (r['notes'] or '') and 'trafikoa' in ((r.get('url') or '') + (r.get('live_stream_url') or '')).lower():
            t += 1
            if t <= 8:
                print('  TRK', r['csv_id'], '|', r['project_name'], '| lat', r['lat'], r['lon'])
print('trafikoa renamed total:', t)
