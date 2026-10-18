"""Madrid Informo cleanup — dedupe 718->366 rows, rectify from official KML, census.

Findings (Session 47c):
  - datos.madrid.es 202088-0-trafico-camaras distributes
    https://informo.madrid.es/informo/tmadrid/CCTV.kml (357 placemarks with
    ExtendedData Nombre + WGS coords + live image URL every 5 min).
  - CSV held 718 informo rows for only 366 unique CamaraNNNNN ids: argus-v2
    ingested every camera TWICE (one series with ?v= cache-buster, one plain)
    and named them from a foreign gazetteer ("Lincoln, Madrid", "Kotzebue,
    Madrid", "Kualapu'u, Madrid"); 13 trafficvision rows (tv_) are clean.
  - 9 CSV ids are absent from the current KML (retired).

Actions per id:
  - keeper: tv_ row if present, else the lower-idx disc_ row; drop the twin.
  - disc keepers: name/lat/lon/geo from KML (rectified-20261017-from-informo-kml).
  - tv keepers: coords from KML only (names are better than KML caps).
  - census: GET https://informo.madrid.es/cameras/{id}.jpg -> refresh
    http_status/live_status/content_type; non-image -> live_status='' +
    image-404@2026-10-17 note; KML-absent -> retired note.

Usage: python -X utf8 camera_testing/_es_madrid_fix.py
"""
import csv
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
KML_PATH = os.path.join(ROOT, 'camera_testing', '_es_madrid_cctv.kml')
STAT_PATH = os.path.join(ROOT, 'camera_testing', '_es_madrid_fix_state.json')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


def parse_kml():
    kml = io.open(KML_PATH, encoding='utf-8', errors='replace').read()
    out = {}
    for p in re.findall(r'<Placemark>(.*?)</Placemark>', kml, re.S):
        m = re.search(r'cameras/(Camara\d+)\.jpg', p)
        if not m:
            continue
        name = re.search(r'<Data name="Nombre">\s*<Value>(.*?)</Value>', p, re.S)
        coords = re.search(r'<coordinates>([-\d.]+),([-\d.]+)', p)
        out[m.group(1)] = {
            'name': (name.group(1).strip() if name else ''),
            'lat': coords.group(2) if coords else '',
            'lon': coords.group(1) if coords else '',
        }
    return out


def probe(cam_id):
    url = f'https://informo.madrid.es/cameras/{cam_id}.jpg'
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            head = r.read(512)
            ctype = (r.headers.get('Content-Type') or '').split(';')[0].strip()
            status = r.status
    except urllib.error.HTTPError as e:
        return cam_id, e.code, (e.headers.get('Content-Type') or '') if e.headers else '', False
    except Exception:
        return cam_id, '', '', False
    is_img = head[:3] == b'\xff\xd8\xff'
    return cam_id, status, ctype, is_img


def main():
    kml = parse_kml()
    print(f'kml placemarks: {len(kml)}')
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    H = {n: i for i, n in enumerate(header)}
    li, ui, idi = H['live_stream_url'], H['url'], H['csv_id']

    groups = {}
    for r in rows[1:]:
        blob = (r[ui] or '') + ' ' + (r[li] or '')
        if 'informo' not in blob.lower():
            continue
        m = re.search(r'(Camara\d+)', blob)
        if not m:
            continue
        groups.setdefault(m.group(1), []).append(r)
    total = sum(len(v) for v in groups.values())
    print(f'informo rows: {total} across {len(groups)} ids')

    keep, drop = {}, []
    for cid, rs in groups.items():
        tv = [r for r in rs if r[idi].startswith('tv_')]
        if tv:
            k = tv[0]
        else:
            k = min(rs, key=lambda r: int(r[0]))
        keep[cid] = k
        drop.extend(id(r) for r in rs if r is not k)
    print(f'keepers: {len(keep)} (tv: {sum(1 for k in keep.values() if k[idi].startswith("tv_"))}), dropping: {len(drop)}')

    print('census: probing', len(groups), 'canonical image URLs ...')
    probe_res = {}
    t0 = time.time()
    with ThreadPoolExecutor(16) as ex:
        futs = [ex.submit(probe, cid) for cid in groups]
        for fut in as_completed(futs):
            cid, status, ctype, is_img = fut.result()
            probe_res[cid] = (status, ctype, is_img)
    print(f'census done in {time.time() - t0:.0f}s')

    stats = {'live': 0, 'dead': 0, 'retired': 0, 'rectified': 0, 'coords_only': 0}
    drop_ids = set(drop)
    for r in rows[1:]:
        if id(r) in drop_ids:
            continue
        cid = next((c for c, k in keep.items() if k is r), None)
        if cid is None:
            continue
        status, ctype, is_img = probe_res.get(cid, ('', '', False))
        r[H['http_status']] = str(status) if status else ''
        r[H['content_type']] = ctype if is_img else (ctype if status == 200 and 'image' in ctype else '')
        if status == 200 and is_img:
            r[H['live_status']] = 'live'
            stats['live'] += 1
        else:
            r[H['live_status']] = ''
            stats['dead'] += 1
            if 'image-404@2026-10-17' not in r[H['notes']]:
                r[H['notes']] = (r[H['notes']] + '; ' if r[H['notes']] else '') + 'image-404@2026-10-17'
        k = kml.get(cid)
        is_tv = r[idi].startswith('tv_')
        if k:
            if r[H['lat']] != k['lat'] or r[H['lon']] != k['lon']:
                r[H['lat']], r[H['lon']] = k['lat'], k['lon']
                r[H['geo_source']] = 'src=informo-kml'
                if not r[H['city']]:
                    r[H['city']] = 'Madrid'
                stats['coords_only' if is_tv else 'rectified'] += 1
            if not is_tv:
                if r[H['project_name']] != k['name']:
                    r[H['project_name']] = k['name']
                if not r[H['url']].endswith('.jpg'):
                    r[H['url']] = f'https://informo.madrid.es/cameras/{cid}.jpg'
                if 'rectified-20261017-from-informo-kml' not in r[H['notes']]:
                    r[H['notes']] = (r[H['notes']] + '; ' if r[H['notes']] else '') + 'rectified-20261017-from-informo-kml'
        else:
            note = 'retired-from-informo-kml@2026-10-17'
            if note not in r[H['notes']]:
                r[H['notes']] = (r[H['notes']] + '; ' if r[H['notes']] else '') + note
            stats['retired'] += 1

    kept_rows = [header] + [r for r in rows[1:] if id(r) not in drop_ids]
    print('result counts:', stats, '| rows', len(rows) - 1, '->', len(kept_rows) - 1)

    lock_fd = None
    for attempt in range(80):
        try:
            lock_fd = os.open(CSV_PATH + '.lock', os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05)
    if lock_fd is None:
        print('[fatal] no lock')
        sys.exit(1)
    try:
        tmp = CSV_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            w.writerows(kept_rows)
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
    json.dump({'stats': stats, 'probes': {k: v[0] for k, v in probe_res.items()}},
              open(STAT_PATH, 'w', encoding='utf-8'), indent=1)
    print('csv rewritten')


if __name__ == '__main__':
    main()
