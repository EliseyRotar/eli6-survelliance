import csv
import json
import os
import re

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
TEMP = os.environ['TEMP']

d = json.load(open(TEMP + r'\mg_arcgis.json', encoding='utf-8'))
cat = {}
for f in d['features']:
    a = f['attributes']
    cat[a['Nome']] = {
        'id': a['idWebcam'], 'concello': a['concello'], 'prov': a['provincia'],
        'dir': a['Directorio'], 'lat': a.get('lat'), 'lon': a.get('lon'),
        'visible': a.get('VisibleWeb'),
    }
print('catalog:', len(cat))
for k, v in sorted(cat.items(), key=lambda x: x[1]['id']):
    print('   %4s | %-26s | %-20s | %-12s | dir=%-16s | %s %s | vis=%s' % (
        v['id'], k, v['concello'], v['prov'], v['dir'], v['lat'], v['lon'], v['visible']))

# existing rows with meteogalicia image urls
existing = {}
with open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        u = (r['live_stream_url'] or '') + ' ' + (r['url'] or '')
        m = re.search(r'datosred/camaras/(\w+)/([\w\d]+)/ultima\.jpg', u)
        if m:
            existing[(m.group(1), m.group(2).lower())] = r
print('\nexisting mg image rows:', len(existing))
for (grp, dirn), r in sorted(existing.items()):
    print('   %-12s %-18s %s | %-42s | lat=%s lon=%s | city=%s' % (
        grp, dirn, r['csv_id'], (r['project_name'] or '')[:42], r['lat'], r['lon'], (r['city'] or '')[:28]))

# match by directorio
cat_dirs = {v['dir'].lower(): k for k, v in cat.items()}
ex_dirs = {d_: k for (g, d_), k in existing.items()}
missing = sorted(set(cat_dirs) - set(ex_dirs))
extra = sorted(set(ex_dirs) - set(cat_dirs))
print('\nMISSING in CSV (catalog cams without row):', missing)
print('CSV dirs not in catalog:', extra)
