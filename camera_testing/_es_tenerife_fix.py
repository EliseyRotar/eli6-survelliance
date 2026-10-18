"""Session-47c: rectify the 96 Tenerife CIC rows + ingest camera TV 1.6.

Source chain:
  - cic.tenerife.es web3 viewer list (listado_camaras_def.html): 96 named cameras
    with cam_web_{A}-{B} ids -> saved camera_testing/_es_tenerife_list.json
  - CIC map DataServer (ele=equ, type=1, zoom>=13): 97 camera markers with official
    coords (realLat/realLon) + current titles; each marker's paramsHtml carries its
    image key camara-{A}-{B}.jpg -> raw: $TEMP/cic_eq_13.json, parsed:
    camera_testing/_es_tenerife_markers.json (keyed A-B after this run)

Fix per row: name <- marker title, lat/lon <- official map point, region/city/road/
org/category/description/likely_subject de-junked, geo_source=src=cic-dataserver,
notes gain cic-group/cic-marker-id. Probed image (row url, e-Traffic3 fallback)
sets http_status/live_status and downloads poster web_viewer/static/posters/{idx}.jpg.

New row: 2701001-61 = "TV 1.6 S. Maria del Mar (M)" (marker 2934, absent from the
viewer list and CSV) -> csv_id cic_240282 (prefix cic added to classifier).

Usage: python -X utf8 camera_testing/_es_tenerife_fix.py
"""
import csv
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
LIST_PATH = os.path.join(ROOT, 'camera_testing', '_es_tenerife_list.json')
MARKERS_RAW = r'C:\Users\ELI6-A~1\AppData\Local\Temp\cic_eq_13.json'
STATE_PATH = os.path.join(ROOT, 'camera_testing', 'es_tenerife_fix_state.json')
POSTER_DIR = os.path.join(ROOT, 'web_viewer', 'static', 'posters')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
SRC_TAG = 'src=cic-dataserver@2026-10-17'


def load_markers():
    """key (A-B) -> {lat, lon, title, mid} from DataServer markers."""
    raw = json.load(open(MARKERS_RAW, encoding='latin-1'))
    out = {}
    no_key = []
    for x in raw:
        m = re.search(r'camara-(\d+)-(\d+)\.jpg', x.get('paramsHtml') or '')
        if not m:
            no_key.append(x.get('id'))
            continue
        key = f'{m.group(1)}-{m.group(2)}'
        out[key] = {'lat': x['realLat'], 'lon': x['realLon'],
                    'title': (x.get('title') or '').strip(), 'mid': str(x.get('id'))}
    return out, no_key


def group_road(group):
    if not group:
        return ''
    m = re.search(r'TF-\d+', group)
    return m.group(0) if m else ''


def probe_and_poster(idx, key, urls):
    """Try candidate image urls; first 200+jpeg wins. Returns (status, ctype, url)."""
    last = ''
    for u in urls:
        if not u:
            continue
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read(524288)
                ctype = r.headers.get('Content-Type', '')
            if len(body) >= 1000 and (b'\xff\xd8' in body[:16] or 'image' in ctype):
                dst = os.path.join(POSTER_DIR, f'{idx}.jpg')
                with open(dst, 'wb') as f:
                    f.write(body)
                return 'live', 'image/jpeg', u
            last = f'small/wrong-ctype:{u}'
        except Exception as e:
            last = f'{type(e).__name__}:{u}'
    return '', '', last


def main():
    markers, no_key = load_markers()
    groups = {e['A'] + '-' + e['B']: e['group'] for e in json.load(open(LIST_PATH, encoding='utf-8'))}
    print(f'[init] markers={len(markers)} (no image key: {no_key}) list-entries={len(groups)}')

    lock = CSV_PATH + '.lock'
    for a in range(80):
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            time.sleep(0.05)
    else:
        sys.exit('[fatal] lock')
    try:
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            rd = csv.DictReader(f)
            cols = rd.fieldnames
            rows = list(rd)
        stats = {'rectified': 0, 'unmatched': [], 'new': 0}
        jobs = []  # (idx, key, [urls]) for probing
        for r in rows:
            blob = (r['url'] or '') + ' ' + (r['live_stream_url'] or '')
            if 'cic.tenerife' not in blob:
                continue
            m = re.search(r'camara-(\d+)-(\d+)\.jpg', blob)
            key = f'{m.group(1)}-{m.group(2)}' if m else None
            mk = markers.get(key)
            if not mk:
                stats['unmatched'].append((r['csv_id'], key))
                continue
            grp = groups.get(key, '')
            old_name = r['project_name']
            r['project_name'] = mk['title']
            if (r['description'] or '').strip() in ('', old_name.strip()):
                r['description'] = mk['title']
            r['likely_subject'] = 'Road traffic camera (Tenerife CIC e-Traffic)'
            r['lat'] = str(mk['lat'])
            r['lon'] = str(mk['lon'])
            r['geo_source'] = 'src=cic-dataserver'
            r['location_precision'] = 'precise'
            r['region'] = 'Canary Islands'
            r['city'] = ''
            r['road'] = group_road(grp)
            r['org'] = 'CIC Tenerife (Cabildo Insular de Tenerife)'
            r['category'] = 'traffic'
            notes = r['notes'] or ''
            if SRC_TAG not in notes:
                extra = [SRC_TAG, f'cic-marker-id={mk["mid"]}']
                if grp:
                    extra.append(f'cic-group={grp}')
                r['notes'] = (notes + '; ' if notes else '') + '; '.join(extra)
            stats['rectified'] += 1
            cands = [r['url'], re.sub(r'e-Traffic\d', 'e-Traffic3', r['url'] or ''),
                     f'https://cic.tenerife.es/e-Traffic3/data/camara-{key}.jpg']
            jobs.append((r['idx'], key, cands, r))

        existing_keys = set()
        for r in rows:
            m = re.search(r'camara-(\d+)-(\d+)\.jpg', (r['url'] or '') + ' ' + (r['live_stream_url'] or ''))
            if m and 'cic.tenerife' in ((r['url'] or '') + (r['live_stream_url'] or '')):
                existing_keys.add(f'{m.group(1)}-{m.group(2)}')
        extra_keys = [k for k in markers if k not in existing_keys]
        next_idx = max(int(r['idx']) for r in rows if r['idx'].isdigit()) + 1
        new_recs = []
        for key in extra_keys:
            mk = markers[key]
            row = {c: '' for c in cols}
            row['idx'] = str(next_idx)
            row['csv_id'] = f'cic_{next_idx:04d}'
            row['project_name'] = mk['title']
            img = f'https://cic.tenerife.es/e-Traffic3/data/camara-{key}.jpg'
            row['url'] = img
            row['live_stream_url'] = img
            row['type'] = 'image'
            row['enabled'] = 'True'
            row['description'] = mk['title']
            row['category'] = 'traffic'
            row['likely_subject'] = 'Road traffic camera (Tenerife CIC e-Traffic)'
            row['country'] = 'Spain'
            row['region'] = 'Canary Islands'
            row['city'] = ''
            row['road'] = 'TF-1'
            row['location_precision'] = 'precise'
            row['lat'] = str(mk['lat'])
            row['lon'] = str(mk['lon'])
            row['geo_source'] = 'src=cic-dataserver'
            row['org'] = 'CIC Tenerife (Cabildo Insular de Tenerife)'
            row['host'] = urlparse(img).netloc
            row['confidence'] = 'high'
            row['notes'] = f'{SRC_TAG}; cic-marker-id={mk["mid"]}; not-in-viewer-list@2026-10-17'
            row['visibility'] = ''
            rows.append(row)
            new_recs.append((row['idx'], key, img))
            stats['new'] += 1
            jobs.append((row['idx'], key, [img], row))
            next_idx += 1

        tmp = CSV_PATH + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV_PATH)
    finally:
        if os.path.exists(lock):
            os.remove(lock)

    print(f"[csv] rectified={stats['rectified']} new={stats['new']} unmatched={stats['unmatched']}")
    if stats['new']:
        print('[new]', [(i, k) for i, k, _ in new_recs])

    results = {}
    ok = dead = 0
    with ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(probe_and_poster, idx, key, urls): idx for idx, key, urls, _ in jobs}
        for fut in as_completed(futs):
            idx = futs[fut]
            status, ctype, url = fut.result()
            results[idx] = status
            ok += bool(status)
            dead += not status
    # apply probe results back onto rows in a second locked pass (status fields)
    lock = CSV_PATH + '.lock'
    for a in range(80):
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            time.sleep(0.05)
    else:
        sys.exit('[fatal] lock2')
    try:
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            rd = csv.DictReader(f)
            cols = rd.fieldnames
            rows = list(rd)
        demoted = []
        for r in rows:
            st = results.get(r['idx'])
            if st is None:
                continue
            if st == 'live':
                r['http_status'] = '200'
                r['content_type'] = 'image/jpeg'
                r['live_status'] = 'live'
            else:
                r['http_status'] = ''
                r['live_status'] = ''
                note = 'image-dead@2026-10-17'
                if note not in (r['notes'] or ''):
                    r['notes'] = (r['notes'] + '; ' if r['notes'] else '') + note
                demoted.append((r['csv_id'], st))
        tmp = CSV_PATH + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV_PATH)
    finally:
        if os.path.exists(lock):
            os.remove(lock)

    json.dump({'stats': {k: v for k, v in stats.items() if k != 'unmatched'},
               'unmatched': stats['unmatched'],
               'new_rows': [[i, k, u] for i, k, u in new_recs],
               'posters': results, 'dead': demoted},
              open(STATE_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'[done] posters_live={ok} posters_dead={dead} dead_rows={demoted}')


if __name__ == '__main__':
    main()
