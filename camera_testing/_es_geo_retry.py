# -*- coding: utf-8 -*-
"""Retry 2 failed Cantur geocodes with adjusted queries."""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
csv.field_size_limit(10**7)

GEO = {
    'cnt_240225': ['Sierra del Híjar, Aguero, Cantabria, España',
                   'Aguero, Cantabria, España'],
    'cnt_240226': ['Valle de Iguña, Cantabria, España',
                   'Tres mares, Cantabria, España'],
}


def nominatim(q):
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
        {'q': q, 'format': 'jsonv2', 'limit': 1, 'countrycodes': 'es'})
    req = urllib.request.Request(url, headers={
        'User-Agent': 'eli6-surveillance-research/1.0 (webcam mapping)'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read(200000).decode('utf-8'))
        if data:
            return float(data[0]['lat']), float(data[0]['lon']), data[0].get('display_name', '')[:90]
    except Exception as e:
        print('  [err]', q, type(e).__name__)
    return None


lock_fd = None
for attempt in range(80):
    try:
        lock_fd = os.open(CSV_PATH + '.lock', os.O_CREAT | os.O_EXCL | os.O_RDWR)
        break
    except FileExistsError:
        time.sleep(0.05)
if lock_fd is None:
    sys.exit('no lock')
try:
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    H = {n: i for i, n in enumerate(rows[0])}
    ok = 0
    for r in rows[1:]:
        cid = r[H['csv_id']]
        if cid in GEO and not r[H['lat']]:
            for q in GEO[cid]:
                g = nominatim(q)
                time.sleep(1.1)
                if g:
                    lat, lon, disp = g
                    r[H['lat']] = str(lat)
                    r[H['lon']] = str(lon)
                    r[H['geo_source']] = 'nominatim'
                    r[H['location_precision']] = 'nominatim-poi'
                    r[H['notes']] = (r[H['notes']] or '') + f'; geocoded={disp}'
                    print(f'  [geo-ok] {cid}: {lat},{lon} {disp}')
                    ok += 1
                    break
    tmp = CSV_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        for row in rows:
            w.writerow(row)
    os.replace(tmp, CSV_PATH)
finally:
    try:
        os.close(lock_fd)
    except OSError:
        pass
    try:
        os.remove(CSV_PATH + '.lock')
    except OSError:
        pass
print('[done] geocoded:', ok)
