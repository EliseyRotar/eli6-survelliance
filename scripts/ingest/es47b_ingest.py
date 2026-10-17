"""Spain Session-47b follow-up ingest — 4 rows from camarasdgt Wayback listings.

Harvest: camera_testing/_es_arch4.py resumed the camarasdgt.es listing crawl
(434 CDX pages; 391 fetched before archive.org went offline). The 583-669
external image URLs (non-infocar/non-camarasEtraffic) reduced to:

  vdc  1  Valdezcaray Debutantes/Llano Rehoyo (La Rioja) - LIVE, overlay ts today
  vdq  1  Valdesquí parking (Segovia)               - stale frame 2026-04-01
  cnt  1  Alto Campoo Pidruecos VALLE (Cantabria)   - stale frame 2025-12-03 + truncated
  esp  1  Puerto del Portalet Frontera (Espalet)    - LIVE, lm today

Everything else in the harvest was already in CSV: 508/510 infocar ids live in
the eTraffic API id space (18/993 known legacy), 8 Navarra gov cams present as
tv_ rows, trafikoa ids present, camarasdgt /images/* are firewalled blog media,
content.esquiades.com path is a dated 2024 archive asset.

Usage: python -X utf8 scripts/ingest/es47b_ingest.py
"""
import csv
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
GEO_PATH = os.path.join(ROOT, 'camera_testing', '_es_geo4.json')
STATE_PATH = os.path.join(ROOT, 'camera_testing', 'es47b_ingest_state.json')
POSTER_DIR = os.path.join(ROOT, 'web_viewer', 'static', 'posters')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

CAMS = [
    {
        'key': 'vdc-valdezcaray-debutantes', 'prefix': 'vdc',
        'project_name': 'Valdezcaray - Debutantes (Llano Rehoyo)',
        'url': 'https://www.valdezcaray.es/webcam/Debutantes/debutantes.jpg',
        'type': 'image', 'live_status': 'live', 'http_status': '200',
        'content_type': 'image/jpeg', 'category': 'scenic',
        'likely_subject': 'Ski-resort webcam (Valdezcaray, La Rioja)',
        'country': 'Spain', 'region': 'La Rioja', 'city': 'Ezcaray', 'road': 'LR-416',
        'org': 'Valdezcaray (La Rioja)',
        'notes': 'source=camarasdgt.es/la-rioja/lr-416 (wayback listing); '
                 'overlay-ts=2026-10-17 18:00 fresh; lm=2026-10-17T16:00:02',
    },
    {
        'key': 'vdq-valdesqui-parking', 'prefix': 'vdq',
        'project_name': 'Valdesqui - Parking',
        'url': 'https://valdesqui.es/~cam/parkingnew.jpg?version=6572',
        'type': 'image', 'live_status': '', 'http_status': '200',
        'content_type': 'image/jpeg', 'category': 'scenic',
        'likely_subject': 'Ski-resort parking webcam (Valdesqui, Segovia)',
        'country': 'Spain', 'region': 'Segovia', 'city': 'Rascafria', 'road': 'SG-615',
        'org': 'Valdesqui (Segovia)',
        'notes': 'stale-frame@2026-04-01; lm=2026-06-24; off-season; '
                 'source=camarasdgt.es/segovia/sg-615 (wayback listing)',
    },
    {
        'key': 'cnt-alto-campoo-valle', 'prefix': 'cnt',
        'project_name': 'Alto Campoo - Pidruecos (VALLE)',
        'url': 'https://cantur.com/camaras/VALLE/VALLE.jpg',
        'type': 'image', 'live_status': '', 'http_status': '200',
        'content_type': 'image/jpeg', 'category': 'scenic',
        'likely_subject': 'Mountain webcam view (Cantur Cantabria)',
        'country': 'Spain', 'region': 'Cantabria', 'city': 'Campoo de los Cobos', 'road': 'CA-183',
        'org': 'Cantur (Cantabria)',
        'notes': 'stale-frame@2025-12-03; jpeg-truncated; '
                 'source=camarasdgt.es/cantabria/ca-183 (wayback listing)',
    },
    {
        'key': 'esp-portalet-frontera', 'prefix': 'esp',
        'project_name': 'Puerto del Portalet - Frontera (Espalet)',
        'url': 'https://www.espalet.eu/webcams/Frontera_18008/000M.jpg',
        'type': 'image', 'live_status': 'live', 'http_status': '200',
        'content_type': 'image/jpeg', 'category': 'scenic',
        'likely_subject': 'Border-pass road webcam (A-136 Puerto del Portalet)',
        'country': 'Spain', 'region': 'Huesca', 'city': '', 'road': 'A-136',
        'org': 'EspAlet / Espace Pourtalet AECT',
        'notes': 'source=camarasdgt.es/huesca/a-136 (wayback listing); '
                 'lm=2026-10-17T19:01; geo=col-du-pourtalet border col',
    },
]


def existing_urls():
    seen = set()
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            for u in (r.get('live_stream_url') or '', r.get('url') or ''):
                if u:
                    seen.add(u.replace('https://', 'http://'))
    return seen


def build_rows(header, geo):
    H = {name: i for i, name in enumerate(header)}
    rows = []
    for c in CAMS:
        g = geo.get(c['prefix']) or {}
        row = [''] * len(header)
        row[H['project_name']] = c['project_name']
        row[H['url']] = c['url']
        row[H['live_stream_url']] = c['url']
        row[H['type']] = c['type']
        row[H['enabled']] = 'True'
        row[H['live_status']] = c['live_status']
        row[H['http_status']] = c['http_status']
        row[H['content_type']] = c['content_type']
        row[H['description']] = c['project_name']
        row[H['category']] = c['category']
        row[H['likely_subject']] = c['likely_subject']
        row[H['country']] = c['country']
        row[H['region']] = c['region']
        row[H['city']] = c['city']
        row[H['road']] = c['road']
        row[H['location_precision']] = 'nominatim-poi'
        row[H['lat']] = g.get('lat', '')
        row[H['lon']] = g.get('lon', '')
        row[H['geo_source']] = 'nominatim-poi'
        row[H['org']] = c['org']
        row[H['host']] = urlparse(c['url']).netloc
        row[H['confidence']] = 'high'
        row[H['notes']] = c['notes']
        row[H['visibility']] = ''
        rows.append((row, c['key'], c['prefix'], c['url']))
    return rows


def write_batch(new_rows, header):
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
    written = []
    try:
        with open(CSV_PATH, encoding='utf-8', newline='') as f:
            rows = list(csv.reader(f))
        next_idx = 0
        for r in rows[1:]:
            try:
                v = int(r[0])
                if v > next_idx:
                    next_idx = v
            except Exception:
                pass
        next_idx += 1
        csv_id_i = header.index('csv_id')
        for row, cid, pfx, img in new_rows:
            row[0] = str(next_idx)
            row[csv_id_i] = f'{pfx}_{next_idx:04d}'
            written.append((next_idx, cid, pfx, img))
            rows.append(row)
            next_idx += 1
        tmp = CSV_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            for r in rows:
                w.writerow(r)
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
    return written


def fetch_poster(idx, img_url):
    dst = os.path.join(POSTER_DIR, f'{idx}.jpg')
    try:
        req = urllib.request.Request(img_url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read(524288)
        if len(body) < 1000:
            return idx, f'small:{len(body)}'
        with open(dst, 'wb') as f:
            f.write(body)
        return idx, 'ok-fetch'
    except Exception as e:
        return idx, f'fail:{type(e).__name__}'


def main():
    geo = json.load(open(GEO_PATH, encoding='utf-8'))
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        header = next(csv.reader(f))
    seen = existing_urls()
    cand = build_rows(header, geo)
    todo = [t for t in cand
            if t[3].replace('https://', 'http://') not in seen]
    print(f'[init] {len(cand)} candidates, {len(cand) - len(todo)} already in csv, {len(todo)} to append')
    if not todo:
        print('[done] nothing to append')
        return
    written = write_batch(todo, header)
    print(f'[csv] appended {len(written)} rows ({written[0][0]}..{written[-1][0]})')
    ok = fail = 0
    state = {}
    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(fetch_poster, idx, img) for idx, cid, pfx, img in written]
        for fut in as_completed(futs):
            idx, status = fut.result()
            state[str(idx)] = status
            if status.startswith('ok'):
                ok += 1
            else:
                fail += 1
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump({'written': [[str(i), c, p, s] for i, c, p, s in written],
                   'posters': state}, f, indent=1)
    print(f'[done] rows={len(written)} posters_ok={ok} posters_fail={fail}')


if __name__ == '__main__':
    main()
