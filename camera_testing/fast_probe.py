"""Fast probe — reads insecam_live_cams.txt but pre-filters URLs that already have
a viewer/video path embedded (e.g. `/cgi-bin/viewer/video.jpg?r=1`) so we don't
need to probe multiple paths — just GET the URL and validate the body.

Add CAM only if weights >= 30.
"""
import csv
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = 'Mozilla/5.0'
CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\fast_probe_log.txt'
TXT_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\insecam_live_cams.txt'

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import probe_lib
import csv_writer


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=200, pool_maxsize=400))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=200, pool_maxsize=400))
    s.headers.update({'User-Agent': UA})
    return s


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def existing_hosts():
    seen = set()
    if not os.path.exists(CSV_PATH):
        return seen
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        for cell in row:
            if not cell:
                continue
            for m in re.finditer(r'(?:https?|rtsp|rtmp|mms)://([^/]+)', cell):
                seen.add(m.group(1).lower())
    return seen


def main():
    s = session()
    seen = existing_hosts()
    log(f'[init] {len(seen)} hosts')

    if not os.path.exists(TXT_PATH):
        log('[err] no txt')
        return

    urls = []
    with open(TXT_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            u = line.strip()
            if not u:
                continue
            urls.append(u)
    log(f'[load] {len(urls)} urls')

    targets = []
    seen_url = set()
    for u in urls:
        m = re.match(r'(?:https?|rtsp)://([^/]+)/(\S+)', u)
        if not m:
            continue
        host_port = m.group(1)
        path = '/' + m.group(2).split('?', 1)[0]
        if host_port in seen:
            continue
        if u in seen_url:
            continue
        seen_url.add(u)
        targets.append((u, host_port, path))

    log(f'[targets] {len(targets)}')

    found = 0
    n = 0
    futs = {}
    with ThreadPoolExecutor(max_workers=120) as ex:
        # Concurrent GETs — no path discovery needed since URL has a path
        for u, hp, path in targets:
            if hp in seen:
                continue
            futs[ex.submit(_probe_exact, s, u, hp, path)] = u

        for fut in as_completed(futs):
            n += 1
            u = futs[fut]
            try:
                res = fut.result(timeout=10)
            except Exception:
                continue
            if res:
                log(f'  HIT {res["url"][:120]} w={res["weight"]}')
                m = re.match(r'(?:https?)://([^/]+)', u)
                if not m:
                    continue
                hp = m.group(1)
                hh = hp.split(':')
                host = hh[0]
                port = int(hh[1]) if len(hh) > 1 else 80
                try:
                    geo = probe_lib.geoip(s, host)
                except Exception:
                    geo = {}
                entry = csv_writer.entry_from_probe(res, {'source': 'insecam_dump'}, geo)
                try:
                    idx = csv_writer.append_one(entry)
                    seen.add(hp)
                    log(f'    ADDED idx={idx}')
                    found += 1
                except Exception as e:
                    log(f'    err: {e}')
            if n % 200 == 0:
                log(f'  progress {n}/{len(targets)}, found={found}')


def _probe_exact(s, url, hp, path):
    try:
        r = s.get(url, timeout=3, allow_redirects=False, verify=False, stream=False)
        ct = r.headers.get('Content-Type', '').lower()
        cl = r.headers.get('Content-Length', '0')
        try:
            cl_n = int(cl)
        except Exception:
            cl_n = 0
        body = r.content[:8192]
        kind = probe_lib.looks_like_live(r.headers, body)
        if not kind:
            return None
        # weight: path-based + content
        if 'viewer/video.jpg' in path or '/cam_1.cgi' in path or '/cam_1.mjpg' in path:
            weight = 50
        elif 'nphMotionJpeg' in path:
            weight = 80
        elif 'axis-cgi' in path:
            weight = 70
        elif 'mjpeg' in path or 'video.cgi' in path:
            weight = 35
        else:
            weight = 25
        # boost
        if 'mjpeg-multipart' in kind or 'matroska' in kind:
            weight += 25
        elif 'jpeg-large' in kind:
            weight += 15
        elif 'jpeg-frame' in kind:
            weight += 5
        if weight < 30:
            return None
        # extract host:port
        m = re.match(r'(?:https?)://([^/]+)', url)
        if not m:
            return None
        host_port = m.group(1)
        hh = host_port.split(':')
        host = hh[0]
        port = int(hh[1]) if len(hh) > 1 else 80
        return {
            'url': url,
            'family': probe_lib._classify(path) if hasattr(probe_lib, '_classify') else 'unknown',
            'stream_kind': kind,
            'content_type': ct,
            'content_length': cl_n,
            'weight': weight,
            'host': host,
            'port': port,
            'ssl': False,
            'http_status': r.status_code,
        }
    except Exception:
        return None


if __name__ == '__main__':
    main()
