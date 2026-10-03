"""Discover public/private webcams via known IP ranges and cam search engines.

1. Search for insecam.org cams
2. Search webcamxp.com / similar
3. Probe common residential IP ranges on cam ports (limited)
4. Use IP-camera.com / similar services
"""
import os
import re
import time
import json
import urllib.request
import ssl
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

OUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\private_cams.json'
LOG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\private_scan.log'


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass


def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception as e:
        return -1, str(e).encode()


def main():
    log('[Private] Starting private cam discovery')

    all_urls = set()

    # 1. webcamera24.com
    log('  webcamera24.com...')
    # They have API but it's a JS app. Try sitemap
    for page in range(1, 10):
        s, body = fetch(f'https://www.webcamera24.com/sitemap.xml?page={page}')
        if s == 200:
            urls = re.findall(r'<loc>(https?://[^<]+)</loc>', body.decode('utf-8', errors='replace'))
            for u in urls:
                all_urls.add(u)
            log(f'    page {page}: {len(urls)} urls')
        time.sleep(1)

    # 2. camx.xhamster.com (NSFW, skip)
    # 3. webcams.travel
    log('  webcams.travel...')
    for page in range(1, 5):
        s, body = fetch(f'https://www.webcams.travel/sitemap.xml?page={page}')
        if s == 200:
            urls = re.findall(r'<loc>(https?://[^<]+)</loc>', body.decode('utf-8', errors='replace'))
            for u in urls:
                all_urls.add(u)
            log(f'    page {page}: {len(urls)} urls')
        time.sleep(1)

    # 4. webcamtaxi.com
    log('  webcamtaxi.com...')
    for path in ['/api/v1/webcams', '/sitemap.xml', '/api/webcams']:
        s, body = fetch(f'https://www.webcamtaxi.com{path}')
        if s == 200:
            urls = re.findall(r'(https?://[^\s"\'<>]+\.jpg[^\s"\'<>]*)', body.decode('utf-8', errors='replace'))
            urls += re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', body.decode('utf-8', errors='replace'))
            for u in urls:
                all_urls.add(u)
            log(f'    {path}: {len(urls)} urls')
        time.sleep(0.5)

    # 5. Earthcam.com
    log('  earthcam.com...')
    for path in ['/sitemap.xml', '/sitemap1.xml', '/sitemap_0.xml']:
        s, body = fetch(f'https://www.earthcam.com{path}')
        if s == 200:
            urls = re.findall(r'<loc>(https?://[^<]+)</loc>', body.decode('utf-8', errors='replace'))
            urls += re.findall(r'(https?://[^\s"\'<>]+/cams/[^\s"\'<>]+)', body.decode('utf-8', errors='replace'))
            for u in urls:
                all_urls.add(u)
            log(f'    {path}: {len(urls)} urls')
        time.sleep(0.5)

    # 6. CamStre.am
    log('  camstre.am...')
    for path in ['/api/cameras', '/sitemap.xml']:
        s, body = fetch(f'https://www.camstre.am{path}')
        if s == 200:
            urls = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', body.decode('utf-8', errors='replace'))
            for u in urls:
                all_urls.add(u)
            log(f'    {path}: {len(urls)} urls')

    # 7. xtreemhost.com
    log('  xtreemhost.com...')
    s, body = fetch('https://xtreemhost.com')
    if s == 200:
        urls = re.findall(r'href="(/[^\s"\'<>]+\.html?)"', body.decode('utf-8', errors='replace'))
        for u in urls[:50]:
            full = f'https://xtreemhost.com{u}'
            s2, b2 = fetch(full)
            if s2 == 200:
                cams = re.findall(r'(https?://[^\s"\'<>]+\.jpg[^\s"\'<>]*)', b2.decode('utf-8', errors='replace'))
                for c in cams:
                    all_urls.add(c)

    # 8. OpenCCTV API (if available)
    log('  opencctv.org...')
    for path in ['/api/v1/cameras', '/api/cameras']:
        s, body = fetch(f'https://www.opencctv.org{path}')
        if s == 200:
            try:
                d = json.loads(body)
                if isinstance(d, list):
                    for c in d:
                        if 'url' in c:
                            all_urls.add(c['url'])
            except:
                pass

    # Save
    with open(OUT, 'w') as f:
        json.dump(sorted(all_urls), f, indent=2)
    log(f'[Done] Saved {len(all_urls)} URLs to {OUT}')


if __name__ == '__main__':
    main()
