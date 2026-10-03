"""For cams with auth, try MJPEG stream via Basic Auth."""

import os
import sys
import csv
import json
import time
import socket
import re
import urllib3
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
VB_CSV = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
PROXY_URL = "http://localhost:8767"


def try_with_auth(host, port, user, pw, path):
    """Try fetching a path with Basic Auth, return body if successful."""
    try:
        sock = socket.create_connection((host, port), timeout=5)
        auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
        req = f'GET {path} HTTP/1.0\r\nHost: {host}\r\nAuthorization: Basic {auth}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            d = sock.recv(1)
            if not d:
                sock.close()
                return None, "no_header"
            buf += d
        # Check for 200 OK
        if b'200 OK' not in buf[:50]:
            sock.close()
            return None, "not_200"
        cl_m = re.search(rb'Content-Length: (\d+)', buf, re.I)
        if cl_m:
            expected = int(cl_m.group(1))
        else:
            expected = 50000  # For multipart
        body_start = buf.find(b'\r\n\r\n') + 4
        body = buf[body_start:]
        # Read full body
        try:
            sock.settimeout(4)
            while len(body) < expected:
                d = sock.recv(8192)
                if not d: break
                body += d
        except socket.timeout: pass
        sock.close()
        return body, "ok"
    except Exception as e:
        return None, f"err: {e}"


def get_vb_session(host, port, user, pw, size="1280x720"):
    """Get WV-HTTP session ID via Basic Auth."""
    try:
        sock = socket.create_connection((host, port), timeout=5)
        seq = int(time.time() * 1000) % 100000
        auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
        req = f'GET /-wvhttp-01-/open.cgi?seq={seq}&priority=0&v=h264:{size} HTTP/1.0\r\nHost: {host}\r\nAuthorization: Basic {auth}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        buf = b''
        try:
            sock.settimeout(4)
            while b'\r\n\r\n' not in buf:
                d = sock.recv(1)
                if not d: break
                buf += d
            body_start = buf.find(b'\r\n\r\n') + 4
            body = buf[body_start:]
            while len(body) < 500:
                d = sock.recv(1024)
                if not d: break
                body += d
        except socket.timeout: pass
        sock.close()
        m = re.search(rb's:=([0-9a-f-]+)', body)
        if m:
            return m.group(1).decode()
    except Exception:
        pass
    return None


def verify_session_stream_auth(host, port, sid, user, pw):
    """Verify MJPEG stream with auth."""
    try:
        sock = socket.create_connection((host, port), timeout=5)
        auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
        req = f'GET /-wvhttp-01-/video?{sid}&seq=1 HTTP/1.0\r\nHost: {host}\r\nAuthorization: Basic {auth}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        buf = b''
        try:
            sock.settimeout(4)
            while b'\r\n\r\n' not in buf:
                d = sock.recv(1)
                if not d: break
                buf += d
            body_start = buf.find(b'\r\n\r\n') + 4
            body = buf[body_start:]
            while len(body) < 5000:
                d = sock.recv(8192)
                if not d: break
                body += d
        except socket.timeout: pass
        sock.close()
        if b'multipart/x-mixed-replace' in buf and b'\xff\xd8\xff' in body[:1000]:
            return True
    except Exception:
        pass
    return False


def main():
    csv.field_size_limit(2**31 - 1)
    print(f"[VB Stream Auth v2] Loading {VB_CSV}")
    with open(VB_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))

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
        targets.append({"host": host, "port": port, "user": auth_user, "pass": auth_pass, "row": row})

    print(f"[VB Stream Auth v2] {len(targets)} cams to process")

    updated = 0
    for i, t in enumerate(targets):
        host = t["host"]
        port = t["port"]
        user = t["user"]
        pw = t["pass"]
        row = t["row"]

        # Open WV-HTTP session with auth
        sid = get_vb_session(host, port, user, pw)
        if sid:
            # Verify stream works with auth
            if verify_session_stream_auth(host, port, sid, user, pw):
                proxy_url = f"{PROXY_URL}/mjpeg/{host}/{port}/1280x720/native"
                direct_url = f"http://{host}:{port}/-wvhttp-01-/video?{sid}&seq=1"
                row["live_stream_url"] = proxy_url
                row["type"] = "video-mjpeg"
                existing_notes = row.get("notes", "") or ""
                if "mjpeg_url=" not in existing_notes:
                    row["notes"] = (existing_notes + f" | mjpeg_url={direct_url}").strip(" |")
                updated += 1
                print(f"  [{i+1}/{len(targets)}] {host}:{port} -> MJPEG (auth)")
                continue
            else:
                # Session worked but stream didn't - maybe needs different size
                for size in ["640x480", "1920x1080"]:
                    sid2 = get_vb_session(host, port, user, pw, size)
                    if sid2 and verify_session_stream_auth(host, port, sid2, user, pw):
                        proxy_url = f"{PROXY_URL}/mjpeg/{host}/{port}/{size}/native"
                        direct_url = f"http://{host}:{port}/-wvhttp-01-/video?{sid2}&seq=1"
                        row["live_stream_url"] = proxy_url
                        row["type"] = "video-mjpeg"
                        existing_notes = row.get("notes", "") or ""
                        if "mjpeg_url=" not in existing_notes:
                            row["notes"] = (existing_notes + f" | mjpeg_url={direct_url}").strip(" |")
                        updated += 1
                        print(f"  [{i+1}/{len(targets)}] {host}:{port} -> MJPEG (auth, {size})")
                        break
                else:
                    # Try image.cgi directly (some cams serve JPEG without auth even when admin is locked)
                    body, status = try_with_auth(host, port, user, pw, '/-wvhttp-01-/image.cgi?v=jpg:1280x720')
                    if body and b'\xff\xd8\xff' in body[:20] and len(body) > 500:
                        proxy_url = f"{PROXY_URL}/mjpeg/{host}/{port}/1280x720"
                        direct_url = f"http://{host}:{port}/-wvhttp-01-/image.cgi?v=jpg:1280x720&seq=1"
                        row["live_stream_url"] = proxy_url
                        row["type"] = "image"  # Just image, not video
                        existing_notes = row.get("notes", "") or ""
                        if "mjpeg_url=" not in existing_notes:
                            row["notes"] = (existing_notes + f" | mjpeg_url={direct_url}").strip(" |")
                        updated += 1
                        print(f"  [{i+1}/{len(targets)}] {host}:{port} -> IMAGE (auth)")
        time.sleep(0.05)

    print(f"\n[VB Stream Auth v2] Updated {updated} cams")

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
