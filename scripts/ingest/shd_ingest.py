"""Shodan guest-scraper ingest (Session 42).

Reads camera_testing/shd_chunk_*.json (Playwright guest-search scrapes),
probes candidates (root + fingerprint paths + links found in live HTML),
ingests verified image endpoints with csv_id_prefix='shd'.
"""
import glob
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\scripts\ingest')
import csv_writer
from netlas_ingest_v2 import (
    AUTH_TITLE_RE, FINGERPRINT_PATHS, GENERIC_PATHS, HTML_IMG_RE,
    JUNK_IMG_RE, is_ip_host, probe_url, pick_verified,
)

CHUNK_GLOB = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\shd_chunk_*.json'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0'
HTML_IMG_RE2 = re.compile(
    r'''(?:src|poster)\s*=\s*['"]([^'"]+\.(?:jpe?g|png|mjpg)(?:\?[^'"]*)?)['"]''', re.I)


def load_candidates():
    seen, out = set(), []
    for path in sorted(glob.glob(CHUNK_GLOB)):
        try:
            rows = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            print(f'skip {os.path.basename(path)}: {e}')
            continue
        for r in rows:
            if not isinstance(r, dict) or r.get('error') or not r.get('url'):
                continue
            u = r['url'].strip()
            if not u.startswith(('http://', 'https://')):
                continue
            pr = urlparse(u)
            if not pr.hostname:
                continue
            port = pr.port or (443 if u.startswith('https') else 80)
            key = f'{pr.hostname}:{port}'
            if key in seen:
                continue
            seen.add(key)
            r['_key'] = key
            r['_root'] = f'{"https" if u.startswith("https") else "http"}://{pr.hostname}:{port}'
            out.append(r)
    return out


def existing_state():
    urls, netloc, ids = set(), set(), set()
    with open(csv_writer.CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        import csv as _csv
        rd = _csv.reader(f)
        next(rd, None)
        for row in rd:
            for i in (2, 3):
                if len(row) > i and row[i]:
                    u = row[i].lower().strip()
                    urls.add(u)
                    try:
                        pr = urlparse(u)
                        if pr.netloc and is_ip_host(pr.netloc):
                            netloc.add(pr.netloc)
                    except Exception:
                        pass
            if len(row) > 35 and row[35]:
                for m in re.finditer(r'shd_id=([^\s;,]+)', row[35]):
                    ids.add(m.group(1))
    return urls, netloc, ids


def html_links(root):
    try:
        r = requests.get(root, timeout=(5, 7), verify=False, headers={'User-Agent': UA})
        if r.status_code != 200 or 'html' not in (r.headers.get('Content-Type') or ''):
            return []
        body = r.text[:60000]
        out = []
        for m in HTML_IMG_RE2.finditer(body):
            link = m.group(1)
            if link.startswith('http'):
                out.append(link.split('#')[0])
            elif link.startswith('/'):
                out.append(root + link)
        return out[:6]
    except Exception:
        return []


def build_candidates(rec):
    blob = ' '.join([
        (rec.get('product') or ''), (rec.get('banner') or ''),
        (rec.get('q') or ''), ' '.join(rec.get('hostnames') or []),
    ]).lower()
    root = rec['_root']
    cands = []
    for keys, paths in FINGERPRINT_PATHS:
        if any(k in blob for k in keys):
            cands.extend(root + p for p in paths)
            break
    cands.extend(root + p for p in GENERIC_PATHS)
    cands.extend(html_links(root))
    out, seen = [], set()
    for c in cands:
        cu = c.lower()
        if cu in seen or JUNK_IMG_RE.search(cu):
            continue
        seen.add(cu)
        out.append(c)
    return out[:12]


def ingest(rec, verified):
    url, ct, nbytes = verified
    pr = urlparse(url)
    host = pr.hostname or ''
    port = pr.port or (443 if url.startswith('https') else 80)
    kind = 'mjpeg-multipart' if 'multipart' in ct else 'jpeg-frame'
    name_base = (rec.get('city') or rec.get('country') or host)
    g = {
        'country': rec.get('country', ''),
        'regionName': '',
        'city': rec.get('city', ''),
        'lat': '',
        'lon': '',
        'isp': (rec.get('org') or ''),
        'org': (rec.get('org') or ''),
        'as': '',
        '_latlon': ('', ''),
    }
    probe_res = {
        'family': 'shodan-guest',
        'stream_kind': kind,
        'host': host,
        'port': port,
        'ssl': url.startswith('https'),
        'url': url,
        'http_status': 200,
        'content_type': ct,
        'content_length': nbytes,
        'weight': 35,
    }
    entry = csv_writer.entry_from_probe(probe_res, {'source': 'shodan'}, g)
    entry['project_name'] = f'{name_base} IP cam ({rec.get("product") or "shodan"})'
    entry['type'] = 'video-mjpeg' if kind == 'mjpeg-multipart' else 'image'
    entry['live_stream_url'] = url
    entry['category'] = ''
    entry['visibility'] = ''
    entry['csv_id_prefix'] = 'shd'
    entry['page_title'] = (rec.get('product') or '')[:200]
    entry['notes'] = (
        f'Family=shodan-guest, kind={kind}, weight=35, source=shodan, '
        f'content-type={ct}, content-length={nbytes}, '
        f'shd_id={rec["_key"]}, shodan_q={rec.get("q", "")}, '
        f'org={rec.get("org", "")}, banner={chr(34)}{(rec.get("banner") or "")[:120]}{chr(34)}'
    )
    return csv_writer.append_one(entry)


def main():
    recs = load_candidates()
    print(f'[init] {len(recs)} unique shodan candidates from chunks')
    urls, netloc, ids = existing_state()
    print(f'[init] existing: {len(urls)} urls, {len(netloc)} ip:ports, {len(ids)} shd ids')
    todo = [r for r in recs if r['_key'] not in ids]
    print(f'[init] {len(todo)} to probe')
    added = 0
    for i, rec in enumerate(todo):
        cands = build_candidates(rec)
        if not cands:
            continue
        verified = pick_verified(cands, workers=6)
        if not verified:
            continue
        v_netloc = urlparse(verified[0]).netloc.lower()
        if verified[0].lower().strip() in urls:
            continue
        if is_ip_host(v_netloc) and v_netloc in netloc:
            continue
        try:
            idx = ingest(rec, verified)
        except Exception as e:
            print(f'  err {rec["_key"]}: {e}')
            continue
        if idx:
            urls.add(verified[0].lower().strip())
            if is_ip_host(v_netloc):
                netloc.add(v_netloc)
            added += 1
            print(f'  +[{idx}] {verified[0][:95]}')
        if (i + 1) % 25 == 0:
            print(f'... probed {i+1}/{len(todo)}, added {added}')
    print(f'[done] {len(todo)} probed, {added} added')


if __name__ == '__main__':
    main()
