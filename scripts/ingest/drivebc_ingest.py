"""DriveBC webcam ingest — 1,068 stills (1,067 API cams + orphan ferry cam 481).

Source: https://www.drivebc.ca/api/webcams/ (exact GeoJSON coords per camera,
captions, orientation, update cadence). Live-feed hunt verdict: no public
video — Axis cameras POST stills into the MOTI ingestion service
(bcgov/DriveBC.ca-Images), TMCBC's 200+ live feeds are internal-only;
public surface = proxied stills + 24h replayTheDay stills.

Batch-appends rows under a single csv lock, then downloads posters.

Usage: python -X utf8 scripts/ingest/drivebc_ingest.py
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
DUMP_PATH = os.path.join(ROOT, 'camera_testing', '_drivebc_webcams_raw.json')
FERRY_PATH = os.path.join(ROOT, 'camera_testing', '_drivebc_ferries.json')
STATE_PATH = os.path.join(ROOT, 'camera_testing', 'drivebc_ingest_state.json')
POSTER_DIR = os.path.join(ROOT, 'web_viewer', 'static', 'posters')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
CSV_ID_PREFIX = 'dbc'

ORIENT = {'N': 'north', 'NE': 'northeast', 'E': 'east', 'SE': 'southeast',
          'S': 'south', 'SW': 'southwest', 'W': 'west', 'NW': 'northwest'}


def ascii_s(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode('ascii')


def build_rows(cams, header):
    H = {name: i for i, name in enumerate(header)}
    rows = []
    for w in sorted(cams, key=lambda x: x['id']):
        cid = w['id']
        name = (w.get('name_override') or w.get('name') or '').strip() or f'DriveBC cam {cid}'
        caption = (w.get('caption_override') or w.get('caption') or '').strip()
        hw = (w.get('highway_display') or w.get('highway') or '').strip()
        region = (w.get('region_name') or '').strip()
        orient = (w.get('orientation') or '').strip()
        loc = w.get('location') or {}
        coords = loc.get('coordinates') or ['', '']
        lon, lat = coords[0], coords[1]
        elev = w.get('elevation')
        period = w.get('update_period_mean')
        is_on = bool(w.get('is_on'))
        stale = bool(w.get('marked_stale'))
        delayed = bool(w.get('marked_delayed'))
        on_demand = bool(w.get('is_on_demand'))

        subj = f'Highway road conditions view looking {ORIENT.get(orient, orient)}'
        if caption:
            subj = ascii_s(caption[:160])

        hw_tag = f'Hwy {hw}' if hw else 'Highway'
        proj = f'{ascii_s(name)} · {hw_tag}'
        if region:
            proj += f' · {region}'
        if not proj.endswith('· BC'):
            proj += ' · BC'

        notes = [
            'Family=drivebc', 'kind=jpeg-still', 'weight=30', 'source=drivebc-api',
            f'cam_id={cid}', f'highway={hw}', f'orientation={orient}',
            f'region={region}', f'elevation={elev}',
            f'update_period_mean={period}s', f'is_on={is_on}',
            f'marked_stale={stale}', f'marked_delayed={delayed}',
            f'is_on_demand={on_demand}', f'group={w.get("group")}',
            'replay=24h-stills:/api/webcams/<id>/replayTheDay/+'
            '/images/replaytheday/<id>/<ts>.jpg',
            'delivery=static-jpg-proxy (no public live video; Axis POST '
            'ingestion; TMCBC live feeds internal)',
        ]

        row = [''] * len(header)
        row[H['project_name']] = proj
        row[H['url']] = f'https://www.drivebc.ca/cameras/{cid}'
        row[H['live_stream_url']] = f'https://www.drivebc.ca/images/{cid}.jpg'
        row[H['type']] = 'image'
        row[H['enabled']] = 'True'
        row[H['live_status']] = 'live' if is_on else ''
        row[H['http_status']] = '200'
        row[H['content_type']] = 'image/jpeg'
        row[H['server_header']] = 'nginx'
        row[H['page_title']] = 'DriveBC - Cameras'
        row[H['description']] = ascii_s(caption)
        row[H['category']] = 'traffic'
        row[H['likely_subject']] = subj
        row[H['country']] = 'Canada'
        row[H['region']] = 'British Columbia'
        row[H['city']] = ''
        row[H['address']] = ascii_s(hw_tag)
        row[H['road']] = ascii_s(hw_tag)
        row[H['location_precision']] = 'api-gps'
        row[H['lat']] = str(lat)
        row[H['lon']] = str(lon)
        row[H['geo_source']] = 'drivebc:api-location'
        row[H['org']] = 'BC Ministry of Transportation and Infrastructure'
        row[H['host']] = 'www.drivebc.ca'
        row[H['confidence']] = 'high' if is_on and not stale else 'medium'
        row[H['notes']] = ', '.join(str(n) for n in notes)
        row[H['visibility']] = ''
        rows.append((row, cid))
    return rows


def existing_ids():
    ids = set()
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            cid = (r.get('csv_id') or '')
            if cid.startswith(CSV_ID_PREFIX + '_'):
                ids.add(cid)
            u = (r.get('url') or '')
            if 'drivebc.ca/cameras/' in u:
                ids.add(u.rstrip('/').rsplit('/', 1)[-1])
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


def fetch_poster(idx, cid):
    dst = os.path.join(POSTER_DIR, f'{idx}.jpg')
    try:
        req = urllib.request.Request(
            f'https://www.drivebc.ca/images/{cid}.jpg', headers=UA)
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
    with open(DUMP_PATH, encoding='utf-8') as f:
        cams = json.load(f)
    # orphan ferry cam 481: live image + API detail but absent from /api/webcams/
    with open(FERRY_PATH, encoding='utf-8') as f:
        ferries = json.load(f)
    if not any(c['id'] == 481 for c in cams):
        loc = next((f['location'] for f in ferries if f['id'] == 14), None)
        cams.append({
            'id': 481,
            'name': 'Upper Arrow Lake Ferry (unlisted)',
            'caption': 'Unlisted camera referenced by Upper Arrow Lake Ferry route; '
                       'serves via image proxy but absent from /api/webcams/ listing.',
            'links': {'imageDisplay': '/images/481.jpg?t=0',
                      'replayTheDay': '/api/webcams/481/replayTheDay/'},
            'highway_display': '', 'highway': '', 'region_name': 'Southern Interior',
            'orientation': '', 'location': loc or {'type': 'Point', 'coordinates': ['', '']},
            'elevation': None, 'is_on': True, 'marked_stale': False,
            'marked_delayed': False, 'is_on_demand': False, 'group': 481,
            'update_period_mean': None, 'https_cam': True,
        })
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        header = next(csv.reader(f))
    already = existing_ids()
    cand = build_rows(cams, header)
    todo = [(row, cid) for row, cid in cand if str(cid) not in already]
    print(f'[init] {len(cand)} cams, {len(already)} already in csv, {len(todo)} to append')
    if not todo:
        print('[done] nothing to append')
        return
    written = write_batch(todo, header)
    print(f'[csv] appended {len(written)} rows ({written[0][0]}..{written[-1][0]})')
    ok = fail = 0
    state = {}
    with ThreadPoolExecutor(16) as ex:
        futs = [ex.submit(fetch_poster, idx, cid) for idx, cid, _ in written]
        for i, fut in enumerate(as_completed(futs), 1):
            idx, status = fut.result()
            state[str(idx)] = status
            if status == 'ok':
                ok += 1
            else:
                fail += 1
            if i % 100 == 0:
                print(f'[posters] {i}/{len(written)} ok={ok} fail={fail}', flush=True)
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump({'written': [[str(i), c, n] for i, c, n in written],
                   'posters': state}, f, indent=1)
    print(f'[done] rows={len(written)} posters_ok={ok} posters_fail={fail}')
    if fail:
        sys.exit(1)


if __name__ == '__main__':
    main()
