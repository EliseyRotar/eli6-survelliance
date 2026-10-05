"""Netlas cam discovery v2.1 — verified ingestion (Session 42).

Anonymous Netlas limits (tested):
  - only start=0 works (start>0 -> 403 hard), so yield = unique queries x 20
  - ~2-3 rapid requests -> 429; 30s cadence tolerated, backoff on 429
  - AND port:NNNN works -> query x port expansion multiplies candidates

v2.1 changes vs v2:
  - port-expanded query list (base title/body queries x common cam ports)
  - 30s base sleep, exponential 429 backoff (120s -> 600s)
  - skip auth-wall items (title unauthorized/login/...)
  - reject logo/icon/banner images on probe
  - dedupe by host:port against ENTIRE existing csv (no near-dup rows)
  - proper provenance: csv_id = nls_XXXX, category/visibility blank

Run detached:
  python scripts/ingest/netlas_ingest_v2.py
Progress: camera_testing/netlas_v2_progress.json
Log:      camera_testing/netlas_v2_log.txt
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer

CSV_PATH = csv_writer.CSV_PATH
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\netlas_v2_log.txt'
PROGRESS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\netlas_v2_progress.json'
API = 'https://app.netlas.io/api/responses/'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0'

BASE_QUERIES = [
    'http.title:"WebcamXP"', 'http.title:"WebcamXP 5"', 'http.body:"WebcamXP"',
    'http.title:"yawcam"', 'http.body:"yawcam"',
    'http.title:"Hikvision"', 'http.body:"HIKVISION"',
    'ssl.cert.subject.cn:Hikvision', 'ssl.cert.subject.o:"Hikvision"',
    'http.title:"Dahua"', 'http.body:"Dahua Technology"',
    'ssl.cert.subject.cn:Dahua', 'ssl.cert.subject.cn:Dahua',
    'http.title:"Blue Iris"', 'http.title:"Reolink"', 'http.title:"Foscam"',
    'http.title:"Wansview"', 'http.title:"Amcrest"', 'http.title:"Vivotek"',
    'http.title:"Edimax"', 'http.title:"D-Link"', 'http.title:"TP-Link"',
    'http.title:"Tenvis"', 'http.title:"AirLive"', 'http.title:"Planet"',
    'http.title:"Compro"', 'http.title:"LevelOne"', 'http.title:"Sricam"',
    'http.title:"HView"', 'http.title:"XiongMai"', 'http.title:"TVT"',
    'http.title:"Everfocus"', 'http.title:"GeoVision"', 'http.title:"ACTi"',
    'http.title:"Bosch"', 'http.title:"Panasonic"', 'http.title:"Sony SNC"',
    'http.title:"Canon Network Camera"', 'http.title:"Samsung Network Camera"',
    'http.title:"Honeywell"', 'http.title:"Lorex"', 'http.title:"Swann"',
    'http.title:"ZOSI"', 'http.title:"Apeman"', 'http.title:"YI Camera"',
    'http.title:"UniFi Video"', 'http.title:"MikroTik"',
    'http.title:"Mobotix"', 'http.title:"GoAhead-Webs"', 'http.title:"IQinVision"',
    'http.title:"Basler"', 'http.title:"Arecont"',
    'http.title:"Network Camera"', 'http.title:"IP Camera"',
    'http.title:"Live View"', 'http.title:"Live View / - AXIS"',
    'http.title:"DVR Web Viewer"', 'http.title:"NVR"', 'http.title:"Camera Viewer"',
    'http.title:"Motion Detect"', 'http.title:"MJPEG"',
    'http.title:"Single JPEG"', 'http.title:"CameraX"', 'http.title:"iVideon"',
    'http.title:"TRASSIR"', 'http.title:"iSpy"',
    'http.body:"go2rtc"', 'http.body:"MjpgStreamer"',
    'http.body:"ISAPI"', 'http.body:"snapshot.cgi"',
    'http.body:"axis-cgi/jpg/image.cgi"', 'http.body:"Live View"',
    'http.body:"network camera"', 'http.body:"IP Camera"',
    'product:"Hikvision IP Camera"', 'product:"Dahua IP Camera"', 'product:"AXIS"',
    'ssl.cert.subject.cn:"Axis Communications"',
]

# common cam service ports; first five run in the initial pass
PORTS = [80, 8080, 8000, 8888, 8443, 8081, 81, 9000, 5000, 8008, 8088,
         9090, 9999, 7000, 34567, 8554, 10000, 443, 8082, 8889]

FINGERPRINT_PATHS = [
    (('hikvision', 'isapi'), ['/ISAPI/Streaming/channels/1/picture']),
    (('dahua',), ['/cgi-bin/snapshot.cgi?channel=1', '/cgi-bin/snapshot.cgi']),
    (('axis', 'live view'), ['/axis-cgi/jpg/image.cgi', '/jpg/image.jpg']),
    (('webcamxp',), ['/cam_1.cgi', '/video.jpg', '/snapshot.jpg']),
    (('blue iris',), ['/mjpg/video.mjpg', '/img.jpg']),
    (('reolink',), ['/cgi-bin/api.cgi?cmd=Snap&channel=0']),
    (('yawcam',), ['/image.jpg']),
    (('go2rtc',), ['/video', '/api/stream.m3u8']),
    (('netdvr', 'netsurveillance', 'dvr web'), ['/tmp/snapshot.jpg', '/snapshot.jpg']),
]
GENERIC_PATHS = [
    '/snapshot.jpg', '/cgi-bin/snapshot.cgi', '/current.jpg',
    '/tmp/snapshot.jpg', '/image.jpg', '/jpg/image.jpg',
    '/ISAPI/Streaming/channels/1/picture', '/mjpg/video.mjpg',
    '/video.mjpg', '/cam_1.cgi', '/axis-cgi/jpg/image.cgi',
]
HTML_IMG_RE = re.compile(r'''(?:src|url|href)\s*=\s*['"]([^'"]+\.(?:jpe?g|png|mjpg|cgi)(?:\?[^'"]*)?)['"]''', re.I)
AUTH_TITLE_RE = re.compile(r'unauthoriz|log\s?in|password|forbidden|not authorized|authorization required|sign\s?in|access denied|401', re.I)
JUNK_IMG_RE = re.compile(r'logo|icon|banner|spinner|placeholder|avatar|loading|blank|favicon|sprite|button|qrcode|qr-code|qr_code|/qr/|watermark|overlay', re.I)


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def build_queries():
    out = []
    for port in PORTS:
        for base in BASE_QUERIES:
            out.append(f'{base} AND port:{port}')
    seen, uniq = set(), []
    for q in out:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            p = json.load(open(PROGRESS_PATH))
            if p.get('version') == 'v2.1':
                return p
        except Exception:
            pass
    return {'version': 'v2.1', 'q_idx': 0, 'added': 0, 'pages': 0, 'fetched': 0}


def save_progress(p):
    try:
        json.dump(p, open(PROGRESS_PATH, 'w'))
    except Exception:
        pass


def existing_state():
    """Return (exact urls set, host:port set, netlas ids set) from csv."""
    urls, netloc, ids = set(), set(), set()

    def add_url(u):
        u = (u or '').lower().strip()
        if not u:
            return
        urls.add(u)
        try:
            pr = urlparse(u)
            if pr.netloc:
                netloc.add(pr.netloc)
        except Exception:
            pass

    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        import csv as _csv
        rd = _csv.reader(f)
        next(rd, None)
        for row in rd:
            if len(row) > 3:
                add_url(row[3])
            if len(row) > 2:
                add_url(row[2])
            if len(row) > 35 and row[35]:
                for m in re.finditer(r'netlas_id=([^\s;,]+)', row[35]):
                    ids.add(m.group(1))
    log(f'[init] {len(urls)} urls, {len(netloc)} host:ports, {len(ids)} netlas ids')
    return urls, netloc, ids


def fetch_page(s, query, base_sleep):
    """start=0 only (anonymous). Returns items list, [] empty, None err/429-exhaust."""
    url = f'{API}?q={urllib.parse.quote(query)}&start=0&indices='
    delay = 120
    for attempt in range(5):
        try:
            r = s.get(url, timeout=25)
            if r.status_code == 429:
                sleep_for = min(delay, 600)
                log(f'  429 -> sleep {sleep_for}s')
                time.sleep(sleep_for)
                delay *= 2
                continue
            if r.status_code == 403:
                time.sleep(base_sleep)
                return []
            if r.status_code == 200:
                time.sleep(base_sleep)
                try:
                    return r.json().get('items', [])
                except Exception:
                    return []
            log(f'  status={r.status_code} for {query[:60]}')
            time.sleep(base_sleep)
            return []
        except Exception as e:
            log(f'  err: {e}')
            time.sleep(5)
    return None


def build_candidates(item):
    d = item.get('data', {})
    ip = d.get('ip', '')
    port = int(d.get('port') or 80)
    proto = d.get('protocol', 'http')
    if not ip or proto not in ('http', 'https'):
        return []
    scheme = 'https' if proto == 'https' or port in (443, 8443) else 'http'
    root = f'{scheme}://{ip}:{port}'
    http_d = d.get('http') or {}
    title = (http_d.get('title') or '').lower()
    body = (http_d.get('body') or '')
    blob = title + ' ' + body.lower()

    cands = []
    for keys, paths in FINGERPRINT_PATHS:
        if any(k in blob for k in keys):
            cands.extend(f'{root}{p}' for p in paths)
            break
    if body and len(body) < 40000:
        for m in HTML_IMG_RE.finditer(body):
            link = m.group(1)
            if link.startswith('http'):
                cands.append(link.split('#')[0])
            elif link.startswith('/'):
                cands.append(f'{root}{link}')
    cands.extend(f'{root}{p}' for p in GENERIC_PATHS)
    cands.append(root + '/')
    out, seen = [], set()
    for c in cands:
        cu = c.lower()
        if cu in seen or JUNK_IMG_RE.search(cu):
            continue
        seen.add(cu)
        out.append(c)
    return out[:10]


def is_ip_host(netloc):
    host = (netloc.split('@')[-1].split(':')[0] or '')
    return host.replace('.', '').isdigit() and host.count('.') == 3


def probe_url(url):
    """Return (url, content_type, nbytes) only for real image streams."""
    if JUNK_IMG_RE.search(url.lower()):
        return None
    try:
        r = requests.get(url, timeout=(5, 7), stream=True, verify=False,
                         headers={'User-Agent': UA})
        if r.status_code != 200:
            r.close()
            return None
        ct = (r.headers.get('Content-Type') or '').lower()
        buf = b''
        for chunk in r.iter_content(4096):
            buf += chunk
            if len(buf) >= 8192:
                break
        r.close()
        if not buf:
            return None
        is_magic = buf[:3] == b'\xff\xd8\xff' or buf[:8] == b'\x89PNG\r\n\x1a\n'
        if 'multipart/x-mixed-replace' in ct or 'image/' in ct:
            if len(buf) >= 4096 or (is_magic and len(buf) >= 2048):
                return url, ct, len(buf)
            return None
        if is_magic and len(buf) >= 2048:
            return url, 'image/jpeg', len(buf)
        low = buf[:300].lower()
        if b'<html' not in low and b'<!doct' not in low and b'{"' not in low:
            if len(buf) >= 8000 and 'javascript' not in ct and 'json' not in ct:
                return url, ct or 'application/octet-stream', len(buf)
    except Exception:
        return None
    return None


def pick_verified(cands, workers=8):
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(probe_url, u): u for u in cands}
        for fut in as_completed(futs):
            try:
                res = fut.result()
            except Exception:
                res = None
            if res:
                return res
    return None


def ingest(item, verified):
    d = item.get('data', {})
    ip = d.get('ip', '')
    port = int(d.get('port') or 0)
    url, ct, nbytes = verified
    http_d = d.get('http') or {}
    title = http_d.get('title') or ''
    geo = d.get('geo') or {}
    loc = geo.get('location') or {}
    subdiv = geo.get('subdivisions') or ['']
    g = {
        'country': geo.get('country', ''),
        'regionName': subdiv[0] if subdiv else '',
        'city': geo.get('city', ''),
        'lat': loc.get('lat', ''),
        'lon': loc.get('lon', ''),
        'isp': d.get('isp', ''),
        'org': d.get('isp', ''),
        'as': '',
        '_latlon': (loc.get('lat', ''), loc.get('lon', '')),
    }
    kind = 'mjpeg-multipart' if 'multipart' in ct else 'jpeg-frame'
    probe_res = {
        'family': 'netlas-discovered',
        'stream_kind': kind,
        'host': ip,
        'port': port,
        'ssl': url.startswith('https'),
        'url': url,
        'http_status': 200,
        'content_type': ct,
        'content_length': nbytes,
        'weight': 35,
    }
    entry = csv_writer.entry_from_probe(probe_res, {'source': 'netlas'}, g)
    entry['project_name'] = (title[:55] + ' cam') if title else f'{ip} IP cam'
    entry['type'] = 'video-mjpeg' if kind == 'mjpeg-multipart' else 'image'
    entry['live_stream_url'] = url
    entry['category'] = ''
    entry['visibility'] = ''
    entry['csv_id_prefix'] = 'nls'
    entry['page_title'] = title[:200]
    entry['notes'] = (
        f'Family=netlas-discovered, kind={kind}, weight=35, '
        f'source=netlas, content-type={ct}, content-length={nbytes}, '
        f'netlas_id={ip}:{port}:{d.get("protocol", "http")}'
    )
    idx = csv_writer.append_one(entry)
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-pages', type=int, default=0, help='0 = run all queries')
    ap.add_argument('--sleep', type=float, default=30.0)
    args = ap.parse_args()

    queries = build_queries()
    log(f'[init] netlas ingest v2.1, {len(queries)} queries ({len(BASE_QUERIES)} bases x {len(PORTS)} ports)')
    urls, netloc, ids = existing_state()
    prog = load_progress()
    q_idx = min(prog.get('q_idx', 0), len(queries))
    added = prog.get('added', 0)
    pages = prog.get('pages', 0)

    s = requests.Session()
    s.headers.update({'User-Agent': UA, 'Accept': 'application/json'})

    while q_idx < len(queries):
        if args.max_pages and pages >= args.max_pages:
            log(f'[done] page budget reached, added={added}')
            break
        q = queries[q_idx]
        log(f'[Q{q_idx}/{len(queries)}] {q[:70]} added={added} pages={pages}')
        items = fetch_page(s, q, args.sleep)
        pages += 1
        if items is None:
            log('[err] fetch exhausted, stopping')
            break
        for item in items:
            d = item.get('data', {})
            ip, port = d.get('ip', ''), int(d.get('port') or 0)
            if not ip or d.get('protocol') not in ('http', 'https'):
                continue
            netlas_id = f'{ip}:{port}:{d.get("protocol", "http")}'
            if netlas_id in ids:
                continue
            ids.add(netlas_id)
            http_d = d.get('http') or {}
            if AUTH_TITLE_RE.search(http_d.get('title') or ''):
                continue
            root = ('https' if d.get('protocol') == 'https' or port in (443, 8443) else 'http') + f'://{ip}:{port}'
            root_netloc = f'{ip}:{port}'
            if is_ip_host(root_netloc) and root_netloc in netloc:
                continue
            cands = build_candidates(item)
            if not cands:
                continue
            verified = pick_verified(cands)
            if not verified:
                continue
            v_netloc = urlparse(verified[0]).netloc.lower()
            if (is_ip_host(v_netloc) and v_netloc in netloc) or verified[0].lower().strip() in urls:
                continue
            try:
                idx = ingest(item, verified)
            except Exception as e:
                log(f'  ingest err {netlas_id}: {e}')
                continue
            if idx:
                urls.add(verified[0].lower().strip())
                netloc.add(v_netloc)
                netloc.add(root_netloc)
                added += 1
                log(f'  +[{idx}] {verified[0][:95]}')
        q_idx += 1
        save_progress({'version': 'v2.1', 'q_idx': q_idx, 'added': added,
                       'pages': pages, 'fetched': q_idx})
    log(f'[finish] q_idx={q_idx} added={added} pages={pages}')


if __name__ == '__main__':
    main()
