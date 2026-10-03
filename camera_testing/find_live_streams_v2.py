"""Probe 37 remaining URL rows for live MJPEG streams."""
import csv
import json
import sys
import time
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
OUT_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\live_streams_v2.json'


def make_session():
    s = requests.Session()
    retries = Retry(total=1, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20))
    return s


# Patterns to try: (path_template, description, content_type_match)
MJPEG_PATTERNS = [
    ('/mjpeg', 'mjpeg'),
    ('/video.mjpg', 'mjpg'),
    ('/video.cgi', 'cgi'),
    ('/mjpg/video.mjpg', 'axis-mjpg'),
    ('/axis-cgi/mjpg/video.cgi', 'axis-mjpg'),
    ('/cgi-bin/mjpeg', 'mjpeg'),
    ('/cgi-bin/faststream.jpg?stream=full&fps=16', 'mjpeg-faststream'),
    ('/control/faststream.jpg?stream=full&fps=16', 'mjpeg-faststream'),
    ('/control/MJPEG.html', 'mjpeg-control'),
    ('/-wvhttp-01-/video.cgi', 'wvhttp'),
    ('/faststream.jpg?stream=full&fps=16', 'mjpeg-faststream'),
    ('/GetData.cgi', 'cgi-get'),
    ('/GetImage.cgi', 'cgi-image'),
    ('/cam_1.cgi', 'webcamxp'),
    ('/cam_1.mjpg', 'webcamxp-mjpg'),
    ('/nphMotionJpeg', 'axis-motion'),
    ('/Jpeg/CamImg.jpg', 'canon'),
    ('/img.jpg', 'gen-img'),
    ('/video', 'gen-video'),
    ('/videostream.cgi', 'gen-stream'),
    ('/live.sdp', 'rtsp-sdp'),
    ('/stream', 'stream'),
    ('/live', 'live'),
    ('/image', 'img'),
    ('/image.jpg', 'img-jpg'),
    ('/snap.jpg', 'snap'),
    ('/tmpfs/snap.jpg', 'tmpfs-snap'),
    ('/snapshot.jpg', 'snap'),
    ('/jpg/image.jpg', 'acti-jpg'),
    ('/snapshot.cgi', 'snap-cgi'),
]


def is_live_jpeg_chunk(headers, body_chunk):
    ct = headers.get('Content-Type', '').lower()
    if 'multipart/x-mixed-replace' in ct:
        return True
    if 'multipart' in ct and 'mixed' in ct:
        return True
    if body_chunk.startswith(b'\xff\xd8'):
        cl = headers.get('Content-Length', '0')
        if cl.isdigit() and int(cl) > 5000:
            return True
        return True
    return False


def probe_url(s, base, timeout=4.0):
    """Try many paths. Return dict or None."""
    parsed = urlparse(base)
    root = f'{parsed.scheme}://{parsed.netloc}'
    candidates = []
    for path, desc in MJPEG_PATTERNS:
        candidates.append((root + path, desc))
    extras = [
        (base, 'orig'),
        (root + '/', 'root'),
    ]
    seen = set()
    uniq = []
    for u, d in extras + candidates:
        if u not in seen:
            seen.add(u)
            uniq.append((u, d))

    for url, desc in uniq:
        try:
            r = s.get(url, timeout=timeout, allow_redirects=True, stream=True)
            ct = r.headers.get('Content-Type', '').lower()
            cl = r.headers.get('Content-Length', '')
            disp = r.headers.get('Content-Disposition', '').lower()
            server = r.headers.get('Server', '').lower()

            if 'multipart' in ct and 'mixed' in ct:
                r.close()
                return {'url': url, 'desc': desc, 'ct': ct, 'cl': cl, 'note': 'multipart stream'}

            if r.status_code == 200:
                chunk = r.content[:4096]
                if chunk.startswith(b'\xff\xd8') and int(cl or 0) >= 5000:
                    r.close()
                    return {'url': url, 'desc': desc, 'ct': ct, 'cl': cl, 'note': 'large jpeg'}
                if chunk.startswith(b'\xff\xd8') and len(chunk) > 5000:
                    r.close()
                    return {'url': url, 'desc': desc, 'ct': ct, 'cl': cl, 'note': 'jpeg'}

            r.close()
        except (requests.exceptions.RequestException, Exception):
            pass
    return None


def main():
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    print(f'Header cols ({len(header)}): {header[:5]}...', flush=True)
    try:
        url_col = header.index('url')
        live_col = header.index('live_stream_url')
    except ValueError:
        print('Col missing')
        print('Header:', header)
        return

    targets = []
    for i, row in enumerate(rows[1:], 1):
        orig = row[url_col].strip() if url_col < len(row) else ''
        live = row[live_col].strip() if live_col < len(row) else ''
        if not orig:
            continue
        if live:
            continue
        if 'INVESTIGATE' in orig.upper():
            base_only = orig.split()[0]
        else:
            base_only = orig
        targets.append((i, base_only))

    print(f'Targets to probe: {len(targets)}', flush=True)

    s = make_session()
    s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    results = []
    t0 = time.time()
    for idx, url in targets:
        try:
            res = probe_url(s, url)
        except Exception as e:
            res = None
            print(f'[{idx}] ERR: {e}', flush=True)
        if res:
            print(f'[{idx}] LIVE: {res["url"]} ({res["note"]}, {res.get("cl","?")})', flush=True)
            results.append({'idx': idx, 'orig_url': url, 'live_url': res['url'], 'desc': res['desc'], 'note': res['note'], 'ct': res['ct']})
        else:
            print(f'[{idx}] DEAD: {url}', flush=True)
            results.append({'idx': idx, 'orig_url': url, 'live_url': None})
    elapsed = time.time() - t0
    print(f'Done in {elapsed:.1f}s. Found {sum(1 for r in results if r["live_url"])} live.', flush=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
