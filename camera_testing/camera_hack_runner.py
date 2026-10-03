"""Camera-Hack integration — comprehensive insecam.org crawl.

Hits /jsoncountries/ to get cam-count per country, then iterates ALL countries
and ALL pages (~10 cams per page). Writes results to a .txt file like Camera-Hack
and pushes into our probe pipeline + CSV.

This is THE primary cam-discovery script now since insecam has the most
well-known open cams.

Based on github.com/LiZ4rDTeam/Camera-Hack but expanded to:
- Iterate ALL countries automatically (not just one)
- Skip duplicates across countries via seen set
- Push into probe pipeline for live validation
- Geo + CSV append
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
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Host': 'www.insecam.org',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': UA,
}

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\camera_hack_log.txt'
TXT_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\insecam_live_cams.txt'

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import probe_lib
import csv_writer
import harvest_lib


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=80, pool_maxsize=80))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=80, pool_maxsize=80))
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
    log(f'[init] {len(seen)} hosts already in CSV')

    # Step 1: get country list via /jsoncountries/
    log('[step1] GET /en/jsoncountries/ ...')
    idx = harvest_lib.fetch_insecam_index(s)
    if not idx:
        log('[err] no JSON index')
        return
    log(f'[step1] got index for {len(idx)} countries. Top 5:')
    for cc, (name, count) in list(idx.items())[:5]:
        log(f'    {cc:3s} {name:30s} count={count}')

    # Step 2: iterate all countries in order of count
    countries = sorted(idx.items(), key=lambda x: -x[1][1])
    total_urls = 0
    found_count = 0
    txt_seen = set()

    with open(TXT_PATH, 'a', encoding='utf-8') as txt_f:
        for cc, (name, count) in countries:
            if count == 0:
                continue
            max_pages = min(10, (count + 9) // 10)  # 10 cams per page in insecam
            for p in range(max_pages):
                url = f'http://www.insecam.org/en/bycountry/{cc}/?page={p}'
                try:
                    r = s.get(url, timeout=8)
                    if r.status_code != 200:
                        break
                    txt = r.text
                    # Camera-Hack regex
                    find_ip = re.findall(r"http://\d+\.\d+\.\d+\.\d+:\d+", txt)
                    # Also extract viewer-style URLs
                    find_viewer = re.findall(r"http://(?:\d+\.\d+\.\d+\.\d+):\d+/[^\"'\s<>]+", txt)
                    all_urls = set(find_ip) | set(find_viewer)
                    txt_urls_in_country = len(all_urls)
                    if txt_urls_in_country == 0:
                        break
                    for u in all_urls:
                        if u in txt_seen:
                            continue
                        txt_seen.add(u)
                        total_urls += 1
                        # write to file like Camera-Hack
                        txt_f.write(f'{u}\n')
                        txt_f.flush()
                        # extract host:port
                        m = re.match(r'http://(\d+\.\d+\.\d+\.\d+):(\d+)', u)
                        if not m:
                            continue
                        host, port = m.group(1), int(m.group(2))
                        full_h = f'{host}:{port}'
                        if full_h in seen:
                            continue
                        seen.add(full_h)
                        # try probing this cam
                        try:
                            res = probe_lib.probe_host(s, host, port, False, 3.0)
                            if res:
                                geo = probe_lib.geoip(s, host)
                                entry = csv_writer.entry_from_probe(res, {'source': 'camera_hack', 'country': cc}, geo)
                                idx_csv = csv_writer.append_one(entry)
                                log(f'  LIVE {cc} idx={idx_csv} {host}:{port} {res["family"]}')
                                found_count += 1
                        except Exception:
                            pass
                        time.sleep(0.4)  # be polite to insecam
                except Exception as e:
                    log(f'[err] {cc} p{p}: {e}')
                    break
                time.sleep(0.2)
        # Rate-limit per country
        time.sleep(1.0)

    log(f'[done] total URLs written: {total_urls}, live cams added: {found_count}')


if __name__ == '__main__':
    main()
