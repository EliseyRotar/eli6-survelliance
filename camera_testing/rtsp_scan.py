"""RTSP probe scanner with parallel probing.

Tries common RTSP ports and paths on cam IPs in parallel.
"""

import os
import sys
import csv
import json
import time
import socket
import re
import concurrent.futures

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
VB_CSV = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "rtsp_scan_progress.json")

RTSP_PATHS = [
    '/stream1',
    '/',
    '/live.sdp',
    '/MediaInput/h264/stream_1',
    '/11',
    '/PSIA/Streaming/channels/101',
    '/onvif/streaming/channels/101',
    '/av0_0',
    '/h264',
    '/video',
    '/cam/realmonitor',
    '/axis-media/media.amp',
    '/livestream/11',
    '/livestream/12',
    '/Streaming/Channels/101',
    '/Streaming/Channels/1',
    '/live/0/av0',
    '/nphMpeg4/nil-640x480',
    '/PSIA/Streaming/tracks/101',
]


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"probed": {}, "found": 0, "findings": {}}


def save_progress(p):
    try:
        tmp = PROGRESS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(p, f)
        os.replace(tmp, PROGRESS_PATH)
    except Exception:
        pass


def try_rtsp(host, port, path, timeout=2):
    """Try RTSP DESCRIBE on host:port/path."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        while b'\r\n\r\n' not in data and len(data) < 4096:
            try:
                d = sock.recv(1024)
                if not d:
                    break
                data += d
            except socket.timeout:
                break
        sock.close()
        if b'RTSP/1.0 200' in data or b'RTSP/1.0 302' in data or b'RTSP/1.0 301' in data:
            m = re.search(rb'Content-Type:\s*([^\r\n]+)', data, re.I)
            ct = m.group(1).decode() if m else 'unknown'
            return {
                "url": f"rtsp://{host}:{port}{path}",
                "content_type": ct.strip(),
                "status": "200",
            }
        elif b'RTSP/1.0 401' in data:
            return {
                "url": f"rtsp://{host}:{port}{path}",
                "content_type": "auth_required",
                "status": "401",
            }
        elif b'RTSP/1.0 404' in data:
            return None
    except (socket.timeout, ConnectionRefusedError, OSError):
        pass
    except Exception:
        pass
    return None


def probe_host(host, port):
    """Try all RTSP paths on one host. Returns first valid endpoint or None."""
    for path in RTSP_PATHS:
        try:
            result = try_rtsp(host, port, path, timeout=2)
            if result:
                return result
        except Exception:
            continue
    return None


def main():
    print(f"[RTSP Scan] Loading {VB_CSV}", flush=True)
    csv.field_size_limit(2**31 - 1)
    with open(VB_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))

    targets = set()
    for row in rows:
        host = row.get("host", "")
        if not host:
            continue
        h = host.rsplit(":", 1)[0]
        targets.add(h)

    targets = sorted(targets)
    print(f"[RTSP Scan] {len(targets)} unique hosts", flush=True)

    progress = load_progress()
    probed = progress.get("probed", {})
    found = progress.get("found", 0)
    findings = progress.get("findings", {})

    todo = []
    for host in targets:
        for port in [554, 8554]:
            key = f"{host}:{port}"
            if key not in probed:
                todo.append((host, port))

    print(f"[RTSP Scan] {len(todo)} (host, port) combos to probe", flush=True)

    start_time = time.time()
    completed = 0

    def do_probe(args):
        host, port = args
        try:
            return (host, port, probe_host(host, port))
        except Exception as e:
            return (host, port, None)

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        for result in executor.map(do_probe, todo):
            host, port, res = result
            key = f"{host}:{port}"
            probed[key] = True
            completed += 1
            if res:
                findings[key] = res
                found += 1
                print(f"  [{completed}/{len(todo)}] RTSP FOUND: {res['url']}", flush=True)
            if completed % 20 == 0:
                progress["probed"] = probed
                progress["found"] = found
                progress["findings"] = findings
                save_progress(progress)
                elapsed = time.time() - start_time
                rate = completed / max(elapsed, 1)
                print(f"  Progress: {completed}/{len(todo)}, found {found}, {rate:.1f}/s", flush=True)

    progress["probed"] = probed
    progress["found"] = found
    progress["findings"] = findings
    save_progress(progress)
    print(f"\n[RTSP Scan] Done. Found {found} RTSP endpoints in {len(todo)} probes.", flush=True)


if __name__ == "__main__":
    main()
