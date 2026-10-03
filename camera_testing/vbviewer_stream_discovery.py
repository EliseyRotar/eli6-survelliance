"""Canon VB cam stream discovery.

For each cam IP, opens a WV-HTTP session and constructs the MJPEG stream URL.
Then stores it as the live_stream_url in the CSV.

Stream URL format:
  http://<host>/mjpeg_proxy/<host>/<port>/1280x720/native
  OR direct (no proxy):
  http://<host>:<port>/-wvhttp-01-/video?<session_id>&seq=1
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
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
VBVIEWER_CSV = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_stream_progress.json")

PROXY_URL = "http://localhost:8767"


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cams_updated": 0}


def save_progress(p):
    try:
        with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(p, f)
    except Exception:
        pass


def get_wv_session(host, port, size="1280x720"):
    """Open WV-HTTP session and return session_id."""
    # Build URL manually to avoid requests URL-encoding the colon in h264:1280x720
    seq = str(int(time.time() * 1000) % 100000)
    url = f"http://{host}:{port}/-wvhttp-01-/open.cgi?seq={seq}&priority=0&v=h264:{size}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        m = re.search(r"s:=([0-9a-f-]+)", r.text)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def verify_session_stream(host, port, session_id, size="1280x720"):
    """Verify that the session can serve MJPEG stream."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        req = f"GET /-wvhttp-01-/video?{session_id}&seq=1 HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\n\r\n"
        sock.send(req.encode())
        # Read response header
        header = b""
        while b"\r\n\r\n" not in header:
            data = sock.recv(1)
            if not data:
                sock.close()
                return False
            header += data
        # Check Content-Type is multipart
        if b"multipart/x-mixed-replace" not in header:
            sock.close()
            return False
        # Read body and look for JPEG SOI marker (first JPEG starts right after header)
        body_start = header.find(b"\r\n\r\n") + 4
        body = header[body_start:]
        # Try to read first 500 bytes of body
        try:
            while len(body) < 500:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                body += chunk
        except socket.timeout:
            pass
        sock.close()
        if b"\xff\xd8\xff" in body[:500]:
            return True
    except Exception:
        pass
    return False


def main():
    progress = load_progress()
    print(f"[VB Stream Discovery] Loading {VBVIEWER_CSV}")
    csv.field_size_limit(2**31 - 1)
    rows = []
    with open(VBVIEWER_CSV, "r", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)

    live_rows = [r for r in rows if r.get("live_status") == "live"]
    print(f"[VB Stream Discovery] {len(live_rows)} live cams to update")

    updated = 0
    for i, row in enumerate(live_rows):
        host = row.get("host", "")
        url = row.get("url", "")
        if not host:
            continue
        # Parse port
        port = 80
        m = re.search(r":(\d+)", host) or re.search(r":(\d+)", url)
        if m:
            port = int(m.group(1))
        # Determine resolution from existing notes/snapshot
        notes = row.get("notes", "") or ""
        # Try 1280x720 first, fall back to 640x480
        for size in ["1280x720", "640x480"]:
            sid = get_wv_session(host, port, size)
            if not sid:
                continue
            verified = verify_session_stream(host, port, sid, size)
            if verified:
                # Build MJPEG proxy URL (most reliable)
                proxy_url = f"{PROXY_URL}/mjpeg/{host}/{port}/{size}/native"
                direct_url = f"http://{host}:{port}/-wvhttp-01-/video?{sid}&seq=1"
                # Update row
                row["live_stream_url"] = proxy_url
                row["type"] = "video-mjpeg"
                row["notes"] = (notes + f" | mjpeg_url={direct_url} | session={sid}").strip(" |")
                updated += 1
                progress["cams_updated"] = updated
                if updated % 5 == 0:
                    save_progress(progress)
                print(f"  [{i+1}/{len(live_rows)}] Updated: {host}:{port} -> {size} MJPEG")
                break
            else:
                if i < 3:
                    print(f"  [{i+1}/{len(live_rows)}] {host}:{port} verify failed (size={size}, sid={sid})")
        time.sleep(0.2)

    # Write back the updated CSV (atomic)
    tmp_path = VBVIEWER_CSV + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for row in rows:
                w.writerow(row)
    os.replace(tmp_path, VBVIEWER_CSV)
    save_progress(progress)
    print(f"\n[VB Stream Discovery] Updated {updated} cams with MJPEG streams")


if __name__ == "__main__":
    main()
