"""Richmond BC TICS dump — all intersection detail pages -> per-camera JPEGs.

Map page (Default.aspx) gives 161 intersections w/ exact lat/lon + icon type.
Each IntersectionDetails.aspx?id=N lists that intersection's cameras as
https://www.richmond.ca/trafficcam/<16-hex-device>_00.jpg (IIS, fresh
Last-Modified ~every 15-30s). Resumable: per-id done flags.

Usage: python -X utf8 scripts/ingest/richmond_dump.py
"""
import json
import os
import re
import sys
import time
import urllib.request

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
MAP_PATH = os.path.join(ROOT, 'camera_testing', 'richmond_map_cams.json')
OUT_PATH = os.path.join(ROOT, 'camera_testing', 'richmond_dump.json')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
DETAIL = ('https://www.richmond.ca/services/transportation/trafficcameras/'
          'IntersectionDetails.aspx?id={id}')

JPG_RE = re.compile(
    r'https://www\.richmond\.ca/trafficcam/([0-9A-Fa-f]{16}_00|[Vv][Dd][Dd]_[A-Za-z0-9._]+)\.jpg',
    re.I)
# nearby markup: try to pair each jpg with a label/heading if present
LABEL_RE = re.compile(
    r'<h[3-6][^>]*>\s*([^<]{2,80})\s*</h[3-6]>|alt=[\x27"]([^<\x27"]{2,80})[\x27"]|'
    r'title=[\x27"]([^<\x27"]{2,80})[\x27"]', re.I)


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(500000), round(time.time() - t0, 2)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), b'', round(time.time() - t0, 2)
    except Exception as e:
        return 0, {'error': type(e).__name__}, b'', round(time.time() - t0, 2)


def load_done():
    if os.path.isfile(OUT_PATH):
        return json.load(open(OUT_PATH, encoding='utf-8'))
    return {}


def save(data):
    tmp = OUT_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, OUT_PATH)


def main():
    cams = json.load(open(MAP_PATH, encoding='utf-8'))
    data = load_done()
    todo = [cid for cid in sorted(cams, key=int)
            if not data.get(cid, {}).get('done') or not data.get(cid, {}).get('cameras')]
    print(f'[init] {len(cams)} intersections, {len(todo)} to fetch')
    for i, cid in enumerate(todo):
        meta = cams[cid]
        st, hdrs, body, dt = http_get(DETAIL.format(id=cid))
        html = body.decode('utf-8', 'replace') if body else ''
        jpgs = list(dict.fromkeys(JPG_RE.findall(html)))
        # map page icon: VideoIcon = frequently-updated live-ish, StaticCameraIcon = static
        data[cid] = {
            'id': cid,
            'name': meta['name'],
            'lat': meta['lat'],
            'lon': meta['lon'],
            'icon': meta['icon'],
            'detail_status': st,
            'detail_dt': dt,
            'cameras': [{'name': h.lower(),
                         'jpg': f'https://www.richmond.ca/trafficcam/{h.lower()}.jpg'}
                        for h in jpgs],
            'done': True,
        }
        if (i + 1) % 20 == 0 or i == len(todo) - 1:
            save(data)
            n_cam = sum(len(v.get('cameras', [])) for v in data.values())
            print(f'[{i+1}/{len(todo)}] intersections={len(data)} cameras={n_cam}')
        time.sleep(0.25)
    save(data)
    n_cam = sum(len(v.get('cameras', [])) for v in data.values())
    bad = [c for c, v in data.items() if v.get('detail_status') != 200 or not v.get('cameras')]
    print(f'[done] intersections={len(data)} cameras={n_cam} empty_or_bad={len(bad)} {bad[:10]}')


if __name__ == '__main__':
    main()
