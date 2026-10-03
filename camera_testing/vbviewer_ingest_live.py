"""Ingest the 45 live VB cams discovered from user-pasted Google results.
For each cam:
1. Get full probe findings (anon streams, auth status, version, internal IP)
2. Get geo info (IP-API)
3. Reverse DNS
4. Save JPEG snapshot for anon cams
5. Append to controllable_Webcams_vbviewer.csv
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
from urllib.parse import urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vbviewer_probe import probe_vb_cam, detect_model_vb

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV_PATH = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
LIVE_CAMS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_live_cams.json")
SNAPSHOT_DIR = os.path.join(WORKDIR, "camera_testing", "vbviewer_snapshots")
IPAPI_CACHE_PATH = os.path.join(WORKDIR, "backups", "ipapi_cache.json")

CSV_HEADER = [
    "idx", "project_name", "url", "live_stream_url", "type", "auth_required",
    "auth_user", "auth_pass", "enabled", "live_status", "http_status",
    "content_type", "server_header", "page_title", "description", "category",
    "likely_subject", "brand", "model", "country", "region", "city", "zip",
    "address", "lat", "lon", "geo_source", "isp", "org", "asn", "reverse_dns",
    "host", "confidence", "notes", "csv_id"
]


def csv_has_header():
    if not os.path.exists(CSV_PATH):
        return False
    try:
        with open(CSV_PATH, "rb") as f:
            return f.read(2048).startswith(b"idx,")
    except Exception:
        return False


def get_next_idx():
    if not os.path.exists(CSV_PATH):
        return 1
    last_idx = 0
    try:
        with open(CSV_PATH, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 32768), 0)
            for line in f.readlines()[-200:]:
                m = re.match(r"^(\d+),", line)
                if m:
                    last_idx = max(last_idx, int(m.group(1)))
    except Exception:
        pass
    return last_idx + 1


def write_header_if_needed():
    if not csv_has_header():
        try:
            with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
                w.writerow(CSV_HEADER)
        except Exception:
            pass


def append_row(row_dict):
    write_header_if_needed()
    try:
        with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            row = []
            for col in CSV_HEADER:
                v = row_dict.get(col, "")
                if isinstance(v, str) and "\n" in v:
                    v = v.replace("\n", " ").replace("\r", " ")
                row.append(str(v) if v is not None else "")
            w.writerow(row)
        return True
    except Exception as e:
        print(f"Append error: {e}", file=sys.stderr)
        return False


def load_ipapi_cache():
    if os.path.exists(IPAPI_CACHE_PATH):
        try:
            with open(IPAPI_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            pass
    return {}


def save_ipapi_cache(cache):
    try:
        with open(IPAPI_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except Exception:
        pass


def geoip(host, cache):
    if host in cache:
        c = cache[host]
        if time.time() - c.get("_ts", 0) < 86400 * 30:
            return c
    try:
        r = requests.get(f"http://ip-api.com/json/{host}", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                data["_ts"] = time.time()
                cache[host] = data
                return data
    except Exception:
        pass
    return {}


def reverse_dns(host):
    try:
        return socket.gethostbyaddr(host)[0]
    except Exception:
        return ""


def save_snapshot(cam, findings):
    """Save a JPEG snapshot to disk."""
    if not findings["anon_streams"]:
        return None
    url = findings["anon_streams"][0]["url"]
    try:
        r = requests.get(url, timeout=10, stream=False, allow_redirects=False)
        if r.status_code == 200 and b'\xff\xd8\xff' in r.content[:20]:
            safe_host = cam["host"].replace(".", "_").replace(":", "_")
            path = os.path.join(SNAPSHOT_DIR, f"{safe_host}.jpg")
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except Exception:
        pass
    return None


def process_cam(cam, idx_counter, ipapi_cache):
    """Process a single cam into CSV row + snapshot."""
    host = cam["host"]
    port = cam["port"]
    use_https = cam.get("use_https", False)
    use_https_str = "s" if use_https else ""

    # Full probe
    findings = probe_vb_cam(host, port=port, use_https=use_https)
    if not findings["is_vb_cam"]:
        return None

    # Geo info
    geo = geoip(host, ipapi_cache)
    rdns = reverse_dns(host)

    # Build notes
    notes_parts = [f"vbviewer_id={host}:{port}{use_https_str}"]
    if findings["version"]:
        notes_parts.append(f"version={findings['version']}")
    if findings["internal_ip"]:
        notes_parts.append(f"internal_ip={findings['internal_ip']}")
    if cam.get("location"):
        notes_parts.append(f"location_hint={cam['location']}")
    if findings["auth_required"]:
        notes_parts.append(f"admin_paths={len(findings['auth_required'])}")

    # Determine URL fields
    if findings["anon_streams"]:
        best = findings["anon_streams"][0]
        live_url = best["url"]
        stream_type = "image" if "image" in best["content_type"] or "jpeg" in best["content_type"] else "video"
        auth_req = "False"
        http_status = best.get("status", 200)
        content_type = best["content_type"]
        live_status = "live"
        # Save snapshot
        snapshot_path = save_snapshot(cam, findings)
        if snapshot_path:
            notes_parts.append(f"snapshot={os.path.basename(snapshot_path)}")
    else:
        # Viewer-only (admin auth required)
        scheme = "https" if use_https else "http"
        live_url = f"{scheme}://{host}:{port}/viewer/live/index.html?lang=en"
        stream_type = "video"
        auth_req = "True"
        http_status = 401 if findings["auth_required"] else 0
        content_type = ""
        live_status = "auth_required"

    # Model detection
    model = findings["model"] or cam.get("model", "Canon VB")
    if "VB-" not in model:
        model = detect_model_vb(findings["title"], findings["version"]) or model

    brand = "Canon" if "VB-" in model else "Canon"  # All VB cams are Canon

    # Build description
    desc_parts = [
        f"{model} network camera (VBViewer) at {host}:{port}.",
        f"Server: {findings['server_header']}.",
        f"Location: {cam.get('location', 'unknown')}.",
    ]
    if findings["version"]:
        desc_parts.append(f"Firmware: {findings['version']}.")
    if findings["internal_ip"]:
        desc_parts.append(f"Internal LAN IP exposed: {findings['internal_ip']}.")
    if rdns:
        desc_parts.append(f"Reverse DNS: {rdns}.")
    if geo.get("country"):
        desc_parts.append(f"Geo: {geo.get('city', '?')}, {geo.get('country', '?')} ({geo.get('isp', '?')}).")
    desc = " ".join(desc_parts)[:500]

    # Category
    if "lg.jp" in rdns or ".go.jp" in rdns or ".ac.jp" in rdns or ".ed.jp" in rdns:
        category = "public"  # Japanese government cams are typically public
    elif cam.get("location", "").endswith("Japan"):
        category = "public"
    else:
        category = "public" if cam.get("location", "").endswith("USA") or "University" in cam.get("location", "") else "private"

    return {
        "idx": idx_counter[0],
        "project_name": f"vbviewer_{host.replace('.', '_').replace(':', '_')}",
        "url": f"http://{host}:{port}/viewer/live/index.html?lang=en",
        "live_stream_url": live_url,
        "type": stream_type,
        "auth_required": auth_req,
        "auth_user": "",
        "auth_pass": "",
        "enabled": "True",
        "live_status": live_status,
        "http_status": http_status,
        "content_type": content_type,
        "server_header": findings["server_header"],
        "page_title": findings["title"] or "Network Camera",
        "description": desc,
        "category": category,
        "likely_subject": "public-space",
        "brand": brand,
        "model": model,
        "country": geo.get("country", ""),
        "region": geo.get("regionName", ""),
        "city": geo.get("city", ""),
        "zip": geo.get("zip", ""),
        "address": "",
        "lat": geo.get("lat", ""),
        "lon": geo.get("lon", ""),
        "geo_source": "ip-api",
        "isp": geo.get("isp", ""),
        "org": geo.get("org", ""),
        "asn": geo.get("as", ""),
        "reverse_dns": rdns,
        "host": host,
        "confidence": "high" if auth_req == "False" else "medium",
        "notes": "; ".join(notes_parts),
        "csv_id": "",
    }


def main():
    print(f"[VB Ingest Live] Loading live cams from {LIVE_CAMS_PATH}")
    with open(LIVE_CAMS_PATH, "r", encoding="utf-8") as f:
        cams = json.load(f)
    print(f"[VB Ingest Live] {len(cams)} live cams to process")

    ipapi_cache = load_ipapi_cache()
    next_idx = get_next_idx()
    print(f"[VB Ingest Live] Starting from idx {next_idx}")

    added = 0
    skipped = 0
    for i, cam in enumerate(cams):
        # Re-probe to get full info
        host = cam.get("live_info", {}).get("host", "")
        port = cam.get("live_info", {}).get("port", 80)
        if not host:
            # Parse from URL
            url = cam.get("url", "")
            m = re.match(r"https?://([^/:]+)(?::(\d+))?", url)
            if m:
                host = m.group(1)
                port = int(m.group(2)) if m.group(2) else 80
                use_https = url.startswith("https://")
            else:
                continue
        else:
            use_https = cam.get("url", "").startswith("https://")

        cam_data = {"host": host, "port": port, "use_https": use_https, "location": cam.get("location", ""), "model": cam.get("model", "")}

        idx_counter = [next_idx + added]
        try:
            row = process_cam(cam_data, idx_counter, ipapi_cache)
        except Exception as e:
            print(f"  Error processing {host}: {e}")
            row = None
        if row:
            if append_row(row):
                added += 1
                print(f"  [{i+1:2d}/{len(cams)}] Added: {host:35s} | {row['model']:25s} | {row['country']:12s} | {row['live_status']}")
            else:
                skipped += 1
        else:
            skipped += 1
            print(f"  [{i+1:2d}/{len(cams)}] Skipped: {host:35s}")
        # Save cache every 10
        if (i + 1) % 10 == 0:
            save_ipapi_cache(ipapi_cache)
        time.sleep(0.3)

    save_ipapi_cache(ipapi_cache)
    print(f"\n[VB Ingest Live] Done. Added {added} cams, skipped {skipped}.")
    print(f"[VB Ingest Live] CSV now at: {CSV_PATH}")


if __name__ == "__main__":
    main()
