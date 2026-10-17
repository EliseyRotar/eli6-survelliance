"""Spain/Andorra Session-47 webcam ingest — 58 new rows across 5 sources.

Sources (authoritative, all stills-only; live-feed hunt verdict: no public MJPEG/
RTSP/HLS on etraffic — image host serves only {id}.jpg, Akamai SPA fallbacks for
/api/*, origin camarasEtraffic blocked, dgt.es viewer taken down 2026-10-09):
  dgt  41  missing eTraffic cams (14 legacy/pre-env/CDX-only + 27 prod-API new ids)
  eusk   9  opendata.euskadi.eus geojson extras (trafikoa.eus host unreachable here)
  cat    1  gencat WFS emap.terrassa.cam01 (absent from CSV)
  cnt    6  Cantur Cantabria mountain webcams (night-IR + timestamp overlay)
  web    1  camarasdgt.es webcam-subtree YouTube embed (SkylineWebcams Benidorm)

Overlaps vs existing CSV were excluded by per-source id space (andorra/vitoria
fully present as tv_ rows; 122/131 euskadi; 98 gencat). Appends under a single
csv lock, then posters (cache-first).

Usage: python -X utf8 scripts/ingest/es47_ingest.py
"""
import csv
import json
import os
import re
import shutil
import sys
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
INV_PATH = os.path.join(ROOT, 'camera_testing', '_es_inventory_final.json')
CEN_PATH = os.path.join(ROOT, 'camera_testing', '_es_census.json')
STATE_PATH = os.path.join(ROOT, 'camera_testing', 'es47_ingest_state.json')
CACHE_DIR = os.path.join(ROOT, 'camera_testing', '_es_cache')
POSTER_DIR = os.path.join(ROOT, 'web_viewer', 'static', 'posters')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

ORG = {
    'dgt': 'Dirección General de Tráfico (DGT)',
    'eusk': 'Eusko Jaurlaritza / opendata.euskadi.eus',
    'cat': 'Generalitat de Catalunya (SCT) / emap.terrassa.cat',
    'cnt': 'Cantur (Cantabria)',
    'web': 'SkylineWebcams (YouTube)',
}


def ascii_s(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode('ascii')


def fstr(v):
    if v is None or v == '':
        return ''
    return str(v)


def build_rows(cams, cen, header):
    H = {name: i for i, name in enumerate(header)}
    rows = []
    for c in sorted(cams, key=lambda x: (x['prefix'], x['key'])):
        pfx = c['prefix']
        img = c['image_url']
        stream = c.get('stream_url') or img
        ctype = ''
        cv = cen.get(c['key']) or {}
        if cv.get('status') == 200:
            ctype = (cv.get('ctype') or '').split(';')[0].strip()
        notes = c.get('notes') or ''
        if c.get('census_lm'):
            notes += (('; ' if notes else '') + 'img_lm=' + c['census_lm'])
        subject = ''
        if pfx in ('dgt', 'eusk', 'cat'):
            road = c.get('road') or ''
            subject = ascii_s(f'Traffic camera on {road}'.strip())
            if c.get('region') or c.get('city'):
                subject += ascii_s(f" near {c.get('city') or c.get('region')}")
        elif pfx == 'cnt':
            subject = 'Mountain webcam view (Cantur Cantabria)'
        elif pfx == 'web':
            subject = 'YouTube live beach webcam stream'
        row = [''] * len(header)
        row[H['project_name']] = ascii_s(c['project_name']) or c['key']
        row[H['url']] = c['url']
        row[H['live_stream_url']] = stream
        row[H['type']] = c['type']
        row[H['enabled']] = 'True'
        row[H['live_status']] = c.get('live_status') or ''
        row[H['http_status']] = c.get('http_status') or ''
        row[H['content_type']] = ctype
        row[H['description']] = ascii_s(c['project_name'])
        row[H['category']] = c['category']
        row[H['likely_subject']] = subject
        row[H['country']] = c['country']
        row[H['region']] = c.get('region') or ''
        row[H['city']] = c.get('city') or ''
        row[H['road']] = c.get('road') or ''
        row[H['location_precision']] = c.get('location_precision') or ''
        row[H['lat']] = fstr(c.get('lat'))
        row[H['lon']] = fstr(c.get('lon'))
        row[H['geo_source']] = c.get('geo_source') or ''
        row[H['org']] = ORG.get(pfx, '')
        row[H['host']] = urlparse(img).netloc
        row[H['confidence']] = 'high'
        row[H['notes']] = notes
        row[H['visibility']] = ''
        rows.append((row, c['key'], pfx, stream, img))
    return rows


def existing_urls():
    seen = set()
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            for u in (r.get('live_stream_url') or '', r.get('url') or ''):
                if u:
                    seen.add(u.replace('https://', 'http://'))
    return seen


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
        for row, cid, pfx, stream, img in new_rows:
            row[0] = str(next_idx)
            row[csv_id_i] = f'{pfx}_{next_idx:04d}'
            written.append((next_idx, cid, pfx, stream, img))
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


def poster_from_cache_or_fetch(idx, key, img_url):
    dst = os.path.join(POSTER_DIR, f'{idx}.jpg')
    safe = re.sub(r'[^\w.-]', '_', key)
    cache = os.path.join(CACHE_DIR, safe + '.img')
    try:
        if os.path.exists(cache) and os.path.getsize(cache) > 1000:
            shutil.copyfile(cache, dst)
            return idx, 'ok-cache'
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
    with open(INV_PATH, encoding='utf-8') as f:
        cams = json.load(f)
    cen = json.load(open(CEN_PATH, encoding='utf-8'))['new']
    # emap cam01 was fetched with a broken url in census; verify clean url now
    emap = [c for c in cams if c['key'] == 'cat-emap-cam01']
    if emap:
        c = emap[0]
        if not c.get('http_status'):
            try:
                req = urllib.request.Request(c['image_url'], headers=UA)
                with urllib.request.urlopen(req, timeout=15) as r:
                    c['http_status'] = str(r.status)
                    c['live_status'] = 'live' if r.status == 200 else ''
                    c['census_lm'] = r.headers.get('Last-Modified', '')
            except Exception:
                c['http_status'] = ''
                c['live_status'] = ''
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        header = next(csv.reader(f))
    seen = existing_urls()
    cand = build_rows(cams, cen, header)
    stream_i = header.index('live_stream_url')
    todo = []
    for row, cid, pfx, stream, img in cand:
        if stream.replace('https://', 'http://') in seen or img.replace('https://', 'http://') in seen:
            continue
        todo.append((row, cid, pfx, stream, img))
    print(f'[init] {len(cand)} candidates, {len(cand) - len(todo)} already in csv, {len(todo)} to append')
    if not todo:
        print('[done] nothing to append')
        return
    written = write_batch(todo, header)
    print(f'[csv] appended {len(written)} rows ({written[0][0]}..{written[-1][0]})')
    ok = fail = 0
    state = {}
    with ThreadPoolExecutor(12) as ex:
        futs = [ex.submit(poster_from_cache_or_fetch, idx, cid, img) for idx, cid, pfx, stream, img in written]
        for fut in as_completed(futs):
            idx, status = fut.result()
            state[str(idx)] = status
            if status.startswith('ok'):
                ok += 1
            else:
                fail += 1
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump({'written': [[str(i), c, p, s] for i, c, p, s, _ in written],
                   'posters': state}, f, indent=1)
    print(f'[done] rows={len(written)} posters_ok={ok} posters_fail={fail}')
    if fail > 12:
        sys.exit(1)


if __name__ == '__main__':
    main()
