"""Camera-Hack fast-dump — just crawls insecam.org and writes URLs to file.

Doesn't probe each cam (slow). All probing happens in the next pipeline cycle
via a separate script that reads the .txt file.
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

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'User-Agent': UA,
}

LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\camera_hack_dump_log.txt'
TXT_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\insecam_live_cams.txt'
CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import harvest_lib


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=60, pool_maxsize=60))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=60, pool_maxsize=60))
    s.headers.update(HEADERS)
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
    log(f'[init] {len(seen)} existing hosts')

    # Load existing URLs already in the txt file
    seen_urls = set()
    if os.path.exists(TXT_PATH):
        with open(TXT_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    seen_urls.add(line)
    log(f'[init] {len(seen_urls)} URLs already in txt')

    # Step 1: get country list
    idx = harvest_lib.fetch_insecam_index(s)
    if not idx:
        log('[err] no JSON index')
        return
    log(f'[step1] {len(idx)} countries, top:')
    total_count = sum(c[1] for c in idx.values())
    log(f'    total ~{total_count} cams at insecam')

    # Step 2: iterate
    countries = sorted(idx.items(), key=lambda x: -x[1][1])
    found_total = 0
    new_total = 0

    with open(TXT_PATH, 'a', encoding='utf-8') as txt_f:
        for cc, (name, count) in countries:
            if count == 0:
                continue
            max_pages = min(50, (count + 9) // 10)
            for p in range(max_pages):
                url = f'http://www.insecam.org/en/bycountry/{cc}/?page={p}'
                try:
                    r = s.get(url, timeout=6)
                    if r.status_code != 200:
                        break
                    txt = r.text
                    # Extract URL patterns
                    ips1 = re.findall(r"http://\d+\.\d+\.\d+\.\d+:\d+", txt)
                    ips2 = re.findall(r"http://(?:\d+\.\d+\.\d+\.\d+):\d+/[^\"'\s<>]+", txt)
                    urls = set(ips1) | set(ips2)
                    if not urls:
                        break
                    found_total += len(urls)
                    for u in urls:
                        if u in seen_urls:
                            continue
                        seen_urls.add(u)
                        new_total += 1
                        txt_f.write(f'{u}\n')
                    txt_f.flush()
                    log(f'  {cc} p{p}: +{len(urls)} urls (new={new_total}, total={found_total})')
                except Exception as e:
                    log(f'[err] {cc} p{p}: {e}')
                    break
                time.sleep(0.15)
            time.sleep(0.4)

    log(f'[done] {new_total} new URLs, {found_total} total parsed')


if __name__ == '__main__':
    main()
