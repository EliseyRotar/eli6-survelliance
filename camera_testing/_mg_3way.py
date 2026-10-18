import csv
import json
import os
import re

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
TEMP = os.environ['TEMP']

js = json.load(open(TEMP + r'\mg_camaras.json', encoding='utf-8'))['listaCamaras']
print('json cams:', len(js))
print('fields:', sorted(js[0].keys()))

def dirn(u):
    m = re.search(r'datosred/camaras/(\w+)/([\w\d]+)/ultima\.jpg', u)
    return (m.group(1), m.group(2).lower()) if m else None

json_by_dir = {}
for c in js:
    k = dirn(c['imaxeCamara'])
    json_by_dir[k] = c
    print('  %-6s | %-24s | %-22s | %-12s | %-16s | %s %s | %s' % (
        c['identificador'], c.get('nomeCamara'), c.get('concello'), c.get('provincia'),
        k[1], c.get('lat'), c.get('lon'), c['dataUltimaAct']))

csv_by_dir = {}
with open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        u = (r['live_stream_url'] or '') + ' ' + (r['url'] or '')
        m = re.search(r'datosred/camaras/(\w+)/([\w\d]+)/ultima\.jpg', u)
        if m:
            csv_by_dir[(m.group(1), m.group(2).lower())] = r

arc = json.load(open(TEMP + r'\mg_arcgis.json', encoding='utf-8'))
arc_dirs = {f['attributes']['Directorio'].lower(): f['attributes'] for f in arc['features']}

print('\nJSON-not-in-CSV:', sorted(set(json_by_dir) - set(csv_by_dir)))
print('CSV-not-in-JSON:', sorted(set(csv_by_dir) - set(json_by_dir)))
print('ArcGIS-not-in-JSON:', sorted(set(arc_dirs) - {d for g, d in json_by_dir}))
print('JSON-not-in-ArcGIS:', sorted({d for g, d in json_by_dir} - set(arc_dirs)))
