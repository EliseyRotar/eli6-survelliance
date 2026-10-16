"""Richmond BC traffic-camera ingest — 597 stills from 161 intersections.

Source: camera_testing/richmond_dump.json (all cameras from
https://www.richmond.ca/services/transportation/trafficcameras/, exact
map-marker lat/lon per intersection). Recon verdict: no internet-exposed
live video (TICS/Genetec is a segregated city network per OIPC 3073);
these JPGs refresh ~every 2 minutes, so type=image live_status=live.

Batch-appends all rows under a single csv lock (one read/one write —
append_one would rewrite the whole CSV per row), then downloads each
JPG as the poster.

Usage: python -X utf8 scripts/ingest/richmond_ingest.py
"""
import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
DUMP_PATH = os.path.join(ROOT, 'camera_testing', 'richmond_dump.json')
STATE_PATH = os.path.join(ROOT, 'camera_testing', 'richmond_ingest_state.json')
POSTER_DIR = os.path.join(ROOT, 'web_viewer', 'static', 'posters')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
CSV_ID_PREFIX = 'ric'

DIR_MAP = {'eb': 'EB', 'nb': 'NB', 'sb': 'SB', 'wb': 'WB',
           'ne': 'NE', 'nw': 'NW', 'se': 'SE', 'sw': 'SW'}


def ascii_s(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode('ascii')


def cam_direction(cam_name):
    m = re.search(r'[_\-](eb|nb|sb|wb|ne|nw|se|sw)(?:$|[_\-\.])', cam_name or '', re.I)
    return DIR_MAP.get(m.group(1).lower(), '') if m else ''


def build_rows(dump, header):
    H = {name: i for i, name in enumerate(header)}
    new_rows = []
    for iid in sorted(dump, key=lambda x: int(x)):
        rec = dump[iid]
        if rec.get('detail_status') != 200:
            continue
        iname = (rec.get('name') or '').strip()
        lat, lon = rec.get('lat', ''), rec.get('lon', '')
        icon = rec.get('icon') or ''
        cams = rec.get('cameras') or []
        # ordinal per intersection so hex-cam names stay unique
        view_n = 0
        for cam in cams:
            jpg = cam.get('jpg') or ''
            if not jpg:
                continue
            view_n += 1
            cname = (cam.get('name') or cam.get('hex') or os.path.basename(jpg)).strip()
            d = cam_direction(cname) or cam_direction(os.path.basename(jpg))
            if d:
                name = f'{iname} {d} · Richmond, BC'
                subject = f'Roadway traffic at {iname}, {d} approach'
            else:
                name = f'{iname} · Richmond, BC' if len(cams) == 1 \
                    else f'{iname} · view {view_n} · Richmond, BC'
                subject = f'Roadway traffic at {iname}'
            notes = (
                'Family=richmond-tics, kind=jpeg-still, weight=30, '
                'source=richmond.ca-trafficcameras, '
                f'intersection_id={iid}, icon={icon}, '
                f'cam_id={cname}, refresh=~2min, '
                'delivery=static-jpg (no public live video; TICS internal)'
            )
            row = [''] * len(header)
            row[H['project_name']] = ascii_s(name)
            row[H['url']] = jpg
            row[H['live_stream_url']] = jpg
            row[H['type']] = 'image'
            row[H['enabled']] = 'True'
            row[H['live_status']] = 'live'
            row[H['http_status']] = '200'
            row[H['content_type']] = 'image/jpeg'
            row[H['server_header']] = 'Microsoft-IIS/10.0'
            row[H['page_title']] = 'City of Richmond Traffic Cameras'
            row[H['description']] = (
                'Traffic-camera still from the City of Richmond traffic '
                'camera map (TICS); image refreshes about every 2 minutes.'
            )
            row[H['category']] = 'traffic'
            row[H['likely_subject']] = ascii_s(subject)
            row[H['country']] = 'Canada'
            row[H['region']] = 'British Columbia'
            row[H['city']] = 'Richmond'
            row[H['address']] = ascii_s(iname)
            row[H['road']] = ascii_s(iname)
            row[H['location_precision']] = 'intersection_marker'
            row[H['lat']] = str(lat)
            row[H['lon']] = str(lon)
            row[H['geo_source']] = 'richmond.ca:trafficcameras-map'
            row[H['org']] = 'City of Richmond'
            row[H['host']] = 'www.richmond.ca'
            row[H['confidence']] = 'high'
            row[H['notes']] = notes
            row[H['visibility']] = ''
            new_rows.append((row, jpg))
    return new_rows


def existing_jpgs():
    urls = set()
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            u = (r.get('url') or '').strip()
            if '/trafficcam/' in u:
                urls.add(u)
    return urls


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
        for row, jpg in new_rows:
            row[0] = str(next_idx)
            # csv_id column
            for i, name in enumerate(header):
                if name == 'csv_id':
                    row[i] = f'{CSV_ID_PREFIX}_{next_idx:04d}'
                    break
            written.append((next_idx, jpg, row[1]))
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


def fetch_poster(idx, jpg):
    dst = os.path.join(POSTER_DIR, f'{idx}.jpg')
    try:
        req = urllib.request.Request(jpg, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
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
        dump = json.load(f)
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        header = next(csv.reader(f))

    already = existing_jpgs()
    cand = build_rows(dump, header)
    todo = [(row, jpg) for row, jpg in cand if jpg not in already]
    print(f'[init] {len(cand)} cameras in dump, {len(already)} already in csv, '
          f'{len(todo)} to append')
    if not todo:
        print('[done] nothing to append')
        return

    written = write_batch(todo, header)
    print(f'[csv] appended {len(written)} rows '
          f'({written[0][0]}..{written[-1][0]})')

    ok = fail = 0
    state = {}
    with ThreadPoolExecutor(16) as ex:
        futs = [ex.submit(fetch_poster, idx, jpg) for idx, jpg, _ in written]
        for i, fut in enumerate(as_completed(futs), 1):
            idx, status = fut.result()
            state[str(idx)] = status
            if status == 'ok':
                ok += 1
            else:
                fail += 1
            if i % 50 == 0:
                print(f'[posters] {i}/{len(written)} ok={ok} fail={fail}', flush=True)
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump({'written': [[str(i), j, n] for i, j, n in written],
                   'posters': state}, f, indent=1)
    print(f'[done] rows={len(written)} posters_ok={ok} posters_fail={fail}')
    if fail:
        sys.exit(1)


if __name__ == '__main__':
    main()
