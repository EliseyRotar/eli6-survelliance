"""BC Ferries terminal-webcam ingest — 58 stills across 43 terminals.

Source: https://www.bcferries.com/current-conditions/webcams (5 major terminals,
per-cam captions) + all 110 /current-conditions/<A>-<B> route pages + brute-force
probe of camN_CODE.jpg on ccimg.bcferries.com (caught 4 unlinked cams:
cam2/3/4_HSB, cam2_PWR). Live-feed hunt verdict: static JPEG only —
Imperva Securesphere in front of ccimg (98.158.84.78, 443 only); origin
cc.bcferries.com (Apache/2.4.6 RHEL) does not serve cam paths; no
MJPEG/RTSP/ONVIF/axis-cgi anywhere; apigateway closed; MQTT (8883) is
vessel tracking only. Images refresh ~5 min (Last-Modified census).

Batch-appends rows under a single csv lock, then downloads posters.

Usage: python -X utf8 scripts/ingest/bcferries_ingest.py
"""
import csv
import json
import os
import sys
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
INV_PATH = os.path.join(ROOT, 'camera_testing', '_bcf_cams_inventory.json')
STATE_PATH = os.path.join(ROOT, 'camera_testing', 'bcferries_ingest_state.json')
POSTER_DIR = os.path.join(ROOT, 'web_viewer', 'static', 'posters')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
CSV_ID_PREFIX = 'bcf'


def ascii_s(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode('ascii')


def build_rows(cams, header):
    H = {name: i for i, name in enumerate(header)}
    rows = []
    for c in sorted(cams, key=lambda x: (x['code'], x['cam_n'])):
        term = c['terminal']
        captions = c.get('captions') or []
        caption = captions[0] if captions else ''
        cam_n = c['cam_n']
        code = c['code']

        if cam_n == 1:
            cam_label = 'cam1'
        else:
            cam_label = f'cam{cam_n}'

        proj = f'BC Ferries {ascii_s(term)} · {cam_label}'
        if caption and caption != 'Traffic at the terminal':
            proj += f' ({ascii_s(caption)})'
        proj += ' · BC'

        if caption:
            subj = ascii_s(caption[:160])
        else:
            subj = f'Terminal traffic camera at {ascii_s(term)}'

        notes = [
            'Family=bcferries', 'kind=jpeg-still', 'weight=30',
            'source=bcferries-webcams', f'cam_file={c["file"]}',
            f'terminal_code={code}', f'caption={caption}',
            'refresh=~5min (Last-Modified census)',
            'delivery=static-jpg (Imperva-protected ccimg.bcferries.com; '
            'no public live video: no MJPEG/RTSP/ONVIF; origin cc.bcferries.com '
            'does not serve cam paths)',
        ]
        if c.get('unlinked'):
            notes.append('unlinked=not-referenced-by-any-public-page (found by URL probe)')

        row = [''] * len(header)
        row[H['project_name']] = proj
        row[H['url']] = 'https://www.bcferries.com/current-conditions/webcams'
        row[H['live_stream_url']] = c['url']
        row[H['type']] = 'image'
        row[H['enabled']] = 'True'
        row[H['live_status']] = 'live'
        row[H['http_status']] = '200'
        row[H['content_type']] = 'image/jpeg'
        row[H['server_header']] = 'Microsoft-IIS/10.0'
        row[H['page_title']] = 'Terminal Webcams | BC Ferries'
        row[H['description']] = ascii_s(caption)
        row[H['category']] = 'traffic'
        row[H['likely_subject']] = subj
        row[H['country']] = 'Canada'
        row[H['region']] = 'British Columbia'
        row[H['city']] = ascii_s(term)
        row[H['address']] = ascii_s(term)
        row[H['road']] = ''
        row[H['location_precision']] = 'nominatim-terminal'
        row[H['lat']] = str(c['lat'])
        row[H['lon']] = str(c['lon'])
        row[H['geo_source']] = 'bcferries:nominatim-terminal'
        row[H['org']] = 'British Columbia Ferry Services Inc. (BC Ferries)'
        row[H['host']] = 'ccimg.bcferries.com'
        row[H['confidence']] = 'high'
        row[H['notes']] = ', '.join(str(n) for n in notes)
        row[H['visibility']] = ''
        rows.append((row, c['file']))
    return rows


def existing_ids():
    ids = set()
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            cid = (r.get('csv_id') or '')
            if cid.startswith(CSV_ID_PREFIX + '_'):
                ids.add(cid)
            u = (r.get('live_stream_url') or '') + '|' + (r.get('url') or '')
            if 'ccimg.bcferries.com/cc/support/terminals/' in u:
                ids.add(u)
    return ids


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
        for row, cid in new_rows:
            row[0] = str(next_idx)
            for i, name in enumerate(header):
                if name == 'csv_id':
                    row[i] = f'{CSV_ID_PREFIX}_{next_idx:04d}'
                    break
            written.append((next_idx, cid, row[1]))
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


def fetch_poster(idx, cam_url):
    dst = os.path.join(POSTER_DIR, f'{idx}.jpg')
    try:
        req = urllib.request.Request(cam_url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read(524288)
        if len(body) < 1000:
            return idx, f'small:{len(body)}'
        with open(dst, 'wb') as f:
            f.write(body)
        return idx, 'ok'
    except Exception as e:
        return idx, f'fail:{type(e).__name__}'


def main():
    with open(INV_PATH, encoding='utf-8') as f:
        cams = json.load(f)
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        header = next(csv.reader(f))
    already = existing_ids()
    cand = build_rows(cams, header)
    todo = [(row, cid) for row, cid in cand if cid not in already and row[header.index('live_stream_url')] not in already]
    print(f'[init] {len(cand)} cams, {len(already)} already in csv, {len(todo)} to append')
    if not todo:
        print('[done] nothing to append')
        return
    written = write_batch(todo, header)
    print(f'[csv] appended {len(written)} rows ({written[0][0]}..{written[-1][0]})')
    # map file -> poster url for downloads
    url_by_file = {c['file']: c['url'] for c in cams}
    ok = fail = 0
    state = {}
    with ThreadPoolExecutor(16) as ex:
        futs = [ex.submit(fetch_poster, idx, url_by_file.get(cid, cid)) for idx, cid, _ in written]
        for i, fut in enumerate(as_completed(futs), 1):
            idx, status = fut.result()
            state[str(idx)] = status
            if status == 'ok':
                ok += 1
            else:
                fail += 1
            if i % 20 == 0:
                print(f'[posters] {i}/{len(written)} ok={ok} fail={fail}', flush=True)
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump({'written': [[str(i), c, n] for i, c, n in written],
                   'posters': state}, f, indent=1)
    print(f'[done] rows={len(written)} posters_ok={ok} posters_fail={fail}')
    if fail:
        sys.exit(1)


if __name__ == '__main__':
    main()
