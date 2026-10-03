"""Ingest the 439 webviewcams.com seeds into the vbviewer CSV."""
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
SEEDS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_webviewcams_seeds.json")
SNAPSHOT_DIR = os.path.join(WORKDIR, "camera_testing", "vbviewer_snapshots")
IPAPI_CACHE_PATH = os.path.join(WORKDIR, "backups", "ipapi_cache.json")
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_webviewcams_progress.json")

CSV_HEADER = [
    "idx", "project_name", "url", "live_stream_url", "type", "auth_required",
    "auth_user", "auth_pass", "enabled", "live_status", "http_status",
    "content_type", "server_header", "page_title", "description", "category",
    "likely_subject", "brand", "model", "country", "region", "city", "zip",
    "address", "lat", "lon", "geo_source", "isp", "org", "asn", "reverse_dns",
    "host", "confidence", "notes", "csv_id"
]


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"scanned": [], "added": 0}


def save_progress(p):
    try:
        with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(p, f)
    except Exception:
        pass


def load_ipapi_cache():
    if os.path.exists(IPAPI_CACHE_PATH):
        try:
            with open(IPAPI_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            pass
    return {}


def save_ipapi_cache(c):
    try:
        os.makedirs(os.path.dirname(IPAPI_CACHE_PATH), exist_ok=True)
        with open(IPAPI_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(c, f)
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


def csv_has_header():
    if not os.path.exists(CSV_PATH):
        return False
    try:
        with open(CSV_PATH, "rb") as f:
            return f.read(2048).startswith(b"idx,")
    except Exception:
        return False


def append_row(row_dict):
    if not csv_has_header():
        try:
            with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
                w.writerow(CSV_HEADER)
        except Exception:
            return False
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
        return False


def parse_host_port(s):
    """Parse host:port string."""
    if "://" in s:
        s = s.split("://", 1)[1]
    if "/" in s:
        s = s.split("/", 1)[0]
    if ":" in s:
        host, port = s.rsplit(":", 1)
        try:
            return host, int(port)
        except ValueError:
            return s, 80
    return s, 80


def resolve_to_ip(host):
    if not host:
        return None
    try:
        socket.inet_aton(host)
        return host
    except Exception:
        try:
            return socket.gethostbyname(host)
        except Exception:
            return None


def process_seed(cam, idx_counter, ipapi_cache, scanned):
    """Process a single webviewcams seed."""
    host_in, default_port = parse_host_port(cam["host"])
    title = cam.get("title", "")
    region = cam.get("region_scraped", "")

    key = f"{host_in}:{default_port}"
    if key in scanned:
        return None
    scanned.add(key)

    # Resolve to IP
    ip = resolve_to_ip(host_in)
    if not ip:
        return None

    # Try probing on the default port first
    findings = probe_vb_cam(ip, port=default_port, use_https=False, timeout=4)
    if not findings["is_vb_cam"]:
        # Try port 80 as fallback
        if default_port != 80:
            findings = probe_vb_cam(ip, port=80, use_https=False, timeout=4)
    if not findings["is_vb_cam"]:
        return None

    geo = geoip(ip, ipapi_cache)
    rdns = reverse_dns(ip)

    notes_parts = [f"vbviewer_id={ip}:{default_port}", f"webviewcams_seed"]
    if findings["version"]:
        notes_parts.append(f"version={findings['version']}")
    if findings["model"]:
        notes_parts.append(f"model={findings['model']}")
    if findings["internal_ip"]:
        notes_parts.append(f"internal_ip={findings['internal_ip']}")
    if title:
        notes_parts.append(f"location={title}")
    if region:
        notes_parts.append(f"region={region}")
    if rdns and rdns != host_in:
        notes_parts.append(f"rdns={rdns}")

    if findings["anon_streams"]:
        best = findings["anon_streams"][0]
        return {
            "url": f"http://{host_in}:{default_port}/viewer/live/index.html?lang=en",
            "live_stream_url": best["url"],
            "type": "image",
            "auth_required": "False",
            "live_status": "live",
            "http_status": 200,
            "content_type": best["content_type"],
            "server_header": findings["server_header"],
            "page_title": findings["title"] or "Network Camera",
            "description": f"VB cam (webviewcams): {title or 'Canon VB'} at {host_in}:{default_port} | {findings['model']} | {findings['version']} | {region}",
            "brand": "Canon",
            "model": findings["model"] or "Canon VB",
            "country": geo.get("country", ""),
            "region": geo.get("regionName", ""),
            "city": geo.get("city", ""),
            "lat": geo.get("lat", ""),
            "lon": geo.get("lon", ""),
            "geo_source": "ip-api",
            "isp": geo.get("isp", ""),
            "org": geo.get("org", ""),
            "asn": geo.get("as", ""),
            "reverse_dns": rdns,
            "host": host_in,
            "category": "public" if geo.get("country") in ("Japan",) or title else "private",
            "likely_subject": "public-space" if geo.get("country") in ("Japan",) else "indoor-residential",
            "confidence": "high",
            "notes": "; ".join(notes_parts),
        }
    elif findings["viewer_page"]:
        return {
            "url": f"http://{host_in}:{default_port}/viewer/live/index.html?lang=en",
            "live_stream_url": f"http://{host_in}:{default_port}/viewer/live/index.html?lang=en",
            "type": "video",
            "auth_required": "True" if findings["auth_required"] else "False",
            "live_status": "auth_required" if findings["auth_required"] else "unknown",
            "http_status": 401 if findings["auth_required"] else 200,
            "content_type": "",
            "server_header": findings["server_header"],
            "page_title": findings["title"] or "Network Camera",
            "description": f"VB cam auth-required (webviewcams): {title or 'Canon VB'} at {host_in}:{default_port} | {findings['model']} | {region}",
            "brand": "Canon",
            "model": findings["model"] or "Canon VB",
            "country": geo.get("country", ""),
            "region": geo.get("regionName", ""),
            "city": geo.get("city", ""),
            "lat": geo.get("lat", ""),
            "lon": geo.get("lon", ""),
            "geo_source": "ip-api",
            "isp": geo.get("isp", ""),
            "org": geo.get("org", ""),
            "asn": geo.get("as", ""),
            "reverse_dns": rdns,
            "host": host_in,
            "category": "public" if geo.get("country") in ("Japan",) or title else "private",
            "likely_subject": "public-space" if geo.get("country") in ("Japan",) else "indoor-residential",
            "confidence": "medium",
            "notes": "; ".join(notes_parts),
        }


def main():
    progress = load_progress()
    ipapi_cache = load_ipapi_cache()
    scanned = set(progress.get("scanned", []))
    print(f"[VB WebViewCams] Already scanned: {len(scanned)} seeds")

    with open(SEEDS_PATH, "r", encoding="utf-8") as f:
        seeds = json.load(f)
    print(f"[VB WebViewCams] Loaded {len(seeds)} seeds from {SEEDS_PATH}")

    next_idx = get_next_idx()
    added = 0
    skipped = 0

    with ThreadPoolExecutor(max_workers=40) as ex:
        futures = {ex.submit(process_seed, s, [next_idx + added], ipapi_cache, scanned): s for s in seeds}
        for i, fut in enumerate(as_completed(futures)):
            try:
                result = fut.result(timeout=15)
            except Exception:
                result = None
            if result:
                result["idx"] = next_idx + added
                result["project_name"] = f"vbviewer_{result['host'].replace('.', '_').replace(':', '_')}"
                if append_row(result):
                    added += 1
                    print(f"  [+] {futures[fut]['host']:45s} | {result['model']:20s} | {result.get('country', '?'):12s} | {result['live_status']}")
                else:
                    skipped += 1
            else:
                skipped += 1
            if (i + 1) % 25 == 0:
                progress["scanned"] = list(scanned)
                progress["added"] = added
                save_progress(progress)
                save_ipapi_cache(ipapi_cache)
                print(f"  ... {i+1}/{len(seeds)} processed (added={added}, skipped={skipped})")

    progress["scanned"] = list(scanned)
    progress["added"] = added
    save_progress(progress)
    save_ipapi_cache(ipapi_cache)
    print(f"\n[VB WebViewCams] Done. Added {added} cams, skipped {skipped}.")


if __name__ == "__main__":
    main()
