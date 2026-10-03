"""For cams with auth_user/auth_pass, try to get MJPEG streams via authenticated session.

Canon VB cams support Basic Auth on most endpoints. The WV-HTTP
getoneshot and image.cgi endpoints may or may not require auth depending on
firmware. We try both.

For each cam with auth, also probe the WV-HTTP /image.cgi with auth.
"""

import os
import sys
import csv
import json
import time
import socket
import re
import requests
import urllib3
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
VB_CSV = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
PROXY_URL = "http://localhost:8767"


def get_session_with_auth(host, port, user, pw, size="1280x720"):
    """Open WV-HTTP session using authenticated requests."""
    # Build URL manually to avoid requests URL-encoding the colon
    url = f"http://{host}:{port}/-wvhttp-01-/open.cgi?seq={int(time.time()*1000)%100000}&priority=0&v=h264:{size}"
    try:
        r = requests.get(url, auth=(user, pw), headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        m = re.search(r"s:=([0-9a-f-]+)", r.text)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def verify_session_with_auth(host, port, sid, user, pw, size="1280x720"):
    """Verify session stream works with auth."""
    try:
        sock = socket.create_connection((host, port), timeout=5)
        req = f'GET /-wvhttp-01-/video?{sid}&seq=1 HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            d = sock.recv(1)
            if not d:
                sock.close()
                return False
            buf += d
        # Check if we need auth (401)
        if b'401' in buf[:300] or b'WWW-Authenticate' in buf[:500]:
            # Need to retry with auth
            try: sock.close()
            except: pass
            sock = socket.create_connection((host, port), timeout=5)
            auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
            req = f'GET /-wvhttp-01-/video?{sid}&seq=1 HTTP/1.0\r\nHost: {host}\r\nAuthorization: Basic {auth}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
            sock.send(req.encode())
            buf = b''
            while b'\r\n\r\n' not in buf:
                d = sock.recv(1)
                if not d:
                    sock.close()
                    return False
                buf += d
        # Check if we have a video stream
        if b'multipart/x-mixed-replace' in buf and b'200 OK' in buf:
            sock.close()
            return True
        sock.close()
    except Exception:
        pass
    return False


def main():
    csv.field_size_limit(2**31 - 1)
    print(f"[VB Stream Auth] Loading {VB_CSV}")
    with open(VB_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))

    # Find cams with auth_user but no MJPEG URL
    targets = []
    for row in rows:
        auth_user = (row.get("auth_user") or "").strip()
        auth_pass = (row.get("auth_pass") or "").strip()
        live_url = row.get("live_stream_url", "") or ""
        if not auth_user or "localhost:8767" in live_url:
            continue
        host = row.get("host", "")
        port = 80
        m = re.search(r":(\d+)$", host)
        if m:
            port = int(m.group(1))
        host = host.rsplit(":", 1)[0]
        targets.append({
            "host": host, "port": port,
            "user": auth_user, "pass": auth_pass,
            "row": row,
        })

    print(f"[VB Stream Auth] {len(targets)} cams need stream URL with auth")

    if not targets:
        return

    updated = 0
    for i, t in enumerate(targets):
        host = t["host"]
        port = t["port"]
        user = t["user"]
        pw = t["pass"]
        row = t["row"]

        # First try without auth
        sid = get_session_with_auth(host, port, "", "")
        if not sid:
            # Try with auth
            sid = get_session_with_auth(host, port, user, pw)

        if not sid:
            continue

        # Verify stream works
        verified = verify_session_with_auth(host, port, sid, user, pw)
        if verified:
            proxy_url = f"{PROXY_URL}/mjpeg/{host}/{port}/1280x720/native"
            direct_url = f"http://{host}:{port}/-wvhttp-01-/video?{sid}&seq=1"
            row["live_stream_url"] = proxy_url
            row["type"] = "video-mjpeg"
            existing_notes = row.get("notes", "") or ""
            if "mjpeg_url=" not in existing_notes:
                row["notes"] = (existing_notes + f" | mjpeg_url={direct_url}").strip(" |")
            updated += 1
            print(f"  [{i+1}/{len(targets)}] {host}:{port} -> MJPEG")
            time.sleep(0.1)

    print(f"\n[VB Stream Auth] Updated {updated} cams")

    # Save CSV
    tmp = VB_CSV + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        w.writerow(list(rows[0].keys()))
        for r in rows:
            w.writerow([r.get(k, "") for k in rows[0].keys()])
    os.replace(tmp, VB_CSV)


if __name__ == "__main__":
    main()
