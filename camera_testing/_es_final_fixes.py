"""Session 47 final CSV fixes: 4 retired Andorra rows, 1 name cosmetic,
Nominatim geocodes for 6 Cantur cams + 2 YouTube beach webcams.

Usage: python -X utf8 camera_testing/_es_final_fixes.py
"""
import csv
import json
import os
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
csv.field_size_limit(10**7)

ANDO = {
    'disc_60721120104': 'Fontaneda (Andorra)',
    'disc_60721120145': 'Radio Andorra Rotonda (Andorra)',
    'disc_60721120148': 'Radio Andorra Sud (Andorra)',
    'disc_60721120153': 'Radio Andorra Nord (Andorra)',
}
GEO = {
    'cnt_240221': 'Abra de Pas golf, Cantabria, España',
    'cnt_240222': 'Calgosa, Cantabria, España',
    'cnt_240223': 'El Chivo, Cantabria, España',
    'cnt_240224': 'Fuente Dé, Cantabria, España',
    'cnt_240225': 'Sierra del Hijar, Cantabria, España',
    'cnt_240226': 'Tres mares, Valle de Iguña, Cantabria, España',
    'web_240277': 'Playa de Benidorm, Benidorm, Alicante, España',
    'tv_146621': 'Playa de Altea, Altea, Alicante, España',
}


def ascii_s(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode('ascii')


def nominatim(q):
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
        {'q': q, 'format': 'jsonv2', 'limit': 1, 'countrycodes': 'es'})
    req = urllib.request.Request(url, headers={
        'User-Agent': 'eli6-surveillance-research/1.0 (webcam mapping)'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read(200000).decode('utf-8'))
        if data:
            d = data[0]
            return float(d['lat']), float(d['lon']), d.get('display_name', '')[:90]
    except Exception as e:
        print(f'  [geo-fail] {q}: {type(e).__name__}')
    return None


def main():
    geo_cache = {}
    lock_fd = None
    for attempt in range(80):
        try:
            lock_fd = os.open(CSV_PATH + '.lock', os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05 + 0.03 * (attempt % 10))
    if lock_fd is None:
        print('[fatal] could not take csv lock')
        sys.exit(1)
    stats = {'ando': 0, 'name': 0, 'geo': 0, 'geo_fail': 0}
    try:
        with open(CSV_PATH, encoding='utf-8', newline='') as f:
            rows = list(csv.reader(f))
        header = rows[0]
        H = {n: i for i, n in enumerate(header)}
        for r in rows[1:]:
            cid = r[H['csv_id']]
            if cid in ANDO:
                if 'rectified-20261017' not in (r[H['notes']] or ''):
                    r[H['project_name']] = ascii_s(ANDO[cid])
                    r[H['region']] = 'Andorra'
                    r[H['category']] = 'traffic'
                    r[H['location_precision']] = 'approximate_from_region'
                    r[H['notes']] = (r[H['notes']] or '') + \
                        '; rectified-20261017-from-official-source; retired-gif (absent from mobilitat API v1)'
                    stats['ando'] += 1
            elif cid == 'cat_240220':
                if ' km  (' in r[H['project_name']]:
                    r[H['project_name']] = r[H['project_name']].replace(' km  (', ' (')
                    stats['name'] += 1
            if cid in GEO and not r[H['lat']]:
                q = GEO[cid]
                if q not in geo_cache:
                    geo_cache[q] = nominatim(q)
                    time.sleep(1.1)
                g = geo_cache[q]
                if g:
                    lat, lon, disp = g
                    r[H['lat']] = str(lat)
                    r[H['lon']] = str(lon)
                    r[H['geo_source']] = 'nominatim'
                    r[H['location_precision']] = 'nominatim-poi'
                    r[H['notes']] = (r[H['notes']] or '') + f'; geocoded={disp}'
                    stats['geo'] += 1
                    print(f'  [geo-ok] {cid}: {lat},{lon} {disp}')
                else:
                    stats['geo_fail'] += 1
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
    print('[stats]', json.dumps(stats))


if __name__ == '__main__':
    main()
