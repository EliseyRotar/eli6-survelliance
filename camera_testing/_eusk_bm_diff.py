import csv, io, os, re

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
existing = {}
with open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        u = (r.get('live_stream_url') or '') + ' ' + (r.get('url') or '')
        if 'bizkaimove' in u.lower():
            m = re.search(r'/cam(\d+)\.jpg', u, re.I)
            if m:
                existing[int(m.group(1))] = r['csv_id']
print('existing bizkaimove cam ids:', len(existing), sorted(existing))

b = open(os.environ['TEMP'] + r'\dfb_en.csv', encoding='utf-8-sig', errors='replace').read()
cat = {}
for x in csv.DictReader(io.StringIO(b)):
    u = (x.get('URL') or '').strip()
    m = re.search(r'/cam(\d+)\.jpg', u, re.I)
    if m:
        n = int(m.group(1))
        cat.setdefault(n, {'url': u, 'names': [], 'row': x})
        cat[n]['names'].append(x.get('IZENA/NOMBRE'))
print('DFB catalog distinct cam ids with url:', len(cat))

new_ids = sorted(set(cat) - set(existing))
dup_ids = sorted(set(cat) & set(existing))
print('overlap (already ingested):', len(dup_ids))
print('TRULY NEW:', len(new_ids), new_ids)
# how many total DFB rows (incl url-less) -> coords-only rows impossible without url
no_url = 0
for x in csv.DictReader(io.StringIO(b)):
    if not (x.get('URL') or '').startswith('http'):
        no_url += 1
print('DFB rows without url:', no_url)
for n in new_ids:
    e = cat[n]
    x = e['row']
    print('  NEW bm%s | %s | %s | lat=%s lon=%s' % (
        n, e['names'][0],
        x.get('ERREPIDEA/CARRETERA'), x.get('PK'),
        (x.get('KOORD_GEOGRAFIKOAK_LATITUDEA/COORD_GEOGRAFICAS_LATITUD') or '').replace(',', '.'),
        (x.get('KOORD_GEOGRAFIKOAK_LONGITUDEA/COORD_GEOGRAFICAS_LONGITUD') or '').replace(',', '.')))
