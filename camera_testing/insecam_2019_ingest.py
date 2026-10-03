"""Insecam 2019 dump ingestion.

17,398 cams from justrandomwebcams/totalynothackedijokeyounot (Feb 2019 insecam snapshot).
Most are dead, but ~500-1500 are still up.

For each, only probe ONCE with a HEAD/light GET — most return 404, those return fast.
For live ones, append to CSV.
"""
import csv
import os
import random
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import probe_lib
import csv_writer

UA = 'Mozilla/5.0'
CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\insecam_2019_log.txt'
DUMP_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\insecam_2019_dump.csv'


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=120, pool_maxsize=240))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=120, pool_maxsize=240))
    s.headers.update({'User-Agent': UA, 'Accept': '*/*'})
    return s


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


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


def parse_dump():
    """Return list of (url, country, city)."""
    if not os.path.exists(DUMP_PATH):
        return []
    rows = []
    with open(DUMP_PATH, 'r', encoding='utf-8') as f:
        rdr = csv.reader(f, delimiter='\t')
        try:
            next(rdr)
        except StopIteration:
            return []
        for row in rdr:
            if len(row) >= 4:
                rows.append((row[3], row[1], row[2]))  # url, country, city
    return rows


def main():
    s = session()
    seen = existing_hosts()
    log(f'[init] {len(seen)} existing hosts')

    rows = parse_dump()
    log(f'[load] {len(rows)} urls from 2019 dump')

    targets = []
    seen_urls = set()
    for url, country, city in rows:
        m = re.match(r'(https?://)([^/]+)(/?\S*)', url)
        if not m:
            continue
        h = m.group(2).lower()
        if h in seen:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        targets.append({'url': url, 'country': country, 'city': city, 'host': h})

    log(f'[targets] {len(targets)}')

    found = 0
    n = 0
    with ThreadPoolExecutor(max_workers=120) as ex:
        futs = {}
        for t in targets:
            futs[ex.submit(_probe_url, s, t['url'], t['host'])] = t
        for fut in as_completed(futs):
            n += 1
            t = futs[fut]
            try:
                res = fut.result(timeout=8)
            except Exception:
                continue
            if res and res.get('weight', 0) >= 30:
                log(f'  HIT {t["url"][:90]} w={res["weight"]} ({t["country"]} {t["city"]})')
                try:
                    geo = probe_lib.geoip(s, t['host'])
                except Exception:
                    geo = {}
                if not geo.get('country'):
                    geo['country'] = t['country']
                if not geo.get('city'):
                    geo['city'] = t['city']
                entry = csv_writer.entry_from_probe(res, {'source': 'insecam_2019'}, geo)
                try:
                    idx = csv_writer.append_one(entry)
                    seen.add(t['host'])
                    log(f'    ADDED idx={idx}')
                    found += 1
                except Exception as e:
                    log(f'    err: {e}')
                time.sleep(0.2)
            if n % 1000 == 0:
                log(f'  progress {n}/{len(targets)}, found={found}')


def _probe_url(s, url, host_port):
    try:
        r = s.get(url, timeout=2.5, allow_redirects=False, stream=True, verify=False)
        ct = r.headers.get('Content-Type', '').lower()
        cl = r.headers.get('Content-Length', '0')
        try:
            cl_n = int(cl)
        except Exception:
            cl_n = 0
        body = r.content[:4096] if r.status_code == 200 else b''
        if r.status_code == 200:
            if 'image' in ct:
                kind = 'jpeg-frame' if cl_n >= 1500 else None
                w = 10 + (15 if cl_n >= 5000 else 0)
            elif 'multipart' in ct:
                kind = 'mjpeg-multipart'
                w = 60
            elif 'video' in ct or 'matroska' in ct:
                kind = 'matroska'
                w = 70
            elif body[:2] == b'\xff\xd8' and len(body) >= 1500:
                kind = 'jpeg-frame'
                w = 10
            else:
                return None
        elif r.status_code == 401:
            return None
        else:
            return None

        m = re.match(r'https?://([^/]+)/?(\S*)', url)
        if not m:
            return None
        hp = m.group(1).split(':')
        host = hp[0]
        port = int(hp[1]) if len(hp) > 1 else 80
        return {
            'url': url,
            'family': 'jpeg' if 'jpeg' in str(kind) else 'unknown',
            'stream_kind': str(kind),
            'content_type': ct,
            'content_length': cl_n,
            'weight': w,
            'host': host,
            'port': port,
            'ssl': False,
            'http_status': r.status_code,
        }
    except Exception:
        return None


if __name__ == '__main__':
    main()
