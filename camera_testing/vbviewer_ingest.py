"""Canon VB / VBViewer cam discovery - aggressive scanner.

Strategy (since OSINT APIs are mostly blocked):
1. Take seed IPs from user's Google results
2. For each seed IP, scan the same /24 subnet for other VB cams (port 80 + WV-HTTP probe)
3. Use Shodan InternetDB (free, no key) to find IPs with http.title:Network Camera patterns
4. Use known subnet ranges where VB cams are commonly deployed
5. Direct probe each candidate IP for anon WV-HTTP

Output: appends to controllable_Webcams_vbviewer.csv (35 columns matching master CSV).
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
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_progress.json")
IPAPI_CACHE_PATH = os.path.join(WORKDIR, "backups", "ipapi_cache.json")
SCANNED_IPS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_scanned_ips.json")

PROBE_TIMEOUT = 5
MAX_WORKERS = 32

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
    return {"cams_added": 0, "scans_run": [], "scanned_ips": []}


def save_progress(progress):
    try:
        os.makedirs(os.path.dirname(PROGRESS_PATH), exist_ok=True)
        with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(progress, f)
    except Exception as e:
        print(f"Save progress error: {e}", file=sys.stderr)


def csv_has_header():
    if not os.path.exists(CSV_PATH):
        return False
    try:
        with open(CSV_PATH, "rb") as f:
            first_bytes = f.read(2048)
        return first_bytes.startswith(b"idx,")
    except Exception:
        return False


def get_next_idx():
    if not os.path.exists(CSV_PATH):
        return 1
    last_idx = 0
    try:
        with open(CSV_PATH, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 16384), 0)
            for line in f.readlines()[-100:]:
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
        except Exception as e:
            print(f"Header write error: {e}", file=sys.stderr)


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
    except Exception as e:
        print(f"Append row error: {e}", file=sys.stderr)
        return False
    return True


def load_caches():
    ipapi_cache = {}
    if os.path.exists(IPAPI_CACHE_PATH):
        try:
            with open(IPAPI_CACHE_PATH, "r", encoding="utf-8") as f:
                ipapi_cache = json.load(f) or {}
        except Exception:
            pass
    return ipapi_cache


def save_ipapi_cache(ipapi_cache):
    try:
        os.makedirs(os.path.dirname(IPAPI_CACHE_PATH), exist_ok=True)
        with open(IPAPI_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(ipapi_cache, f)
    except Exception:
        pass


def geoip(host, ipapi_cache):
    if host in ipapi_cache:
        cached = ipapi_cache[host]
        if time.time() - cached.get("_ts", 0) < 86400 * 30:
            return cached
    try:
        r = requests.get(f"http://ip-api.com/json/{host}", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                data["_ts"] = time.time()
                ipapi_cache[host] = data
                return data
    except Exception:
        pass
    return {}


def reverse_dns_lookup(host):
    try:
        return socket.gethostbyaddr(host)[0]
    except Exception:
        return ""


def load_scanned_ips():
    if os.path.exists(SCANNED_IPS_PATH):
        try:
            with open(SCANNED_IPS_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def save_scanned_ips(ips):
    try:
        os.makedirs(os.path.dirname(SCANNED_IPS_PATH), exist_ok=True)
        with open(SCANNED_IPS_PATH, "w", encoding="utf-8") as f:
            json.dump(list(ips), f)
    except Exception:
        pass


# Seed IPs (from user's Google results)
SEED_IPS = [
    "202.174.60.121",  # VB-M42
    "218.42.253.97",   # VB-M42
    "219.111.32.218",  # dead
    "183.77.125.199",  # VB-S900F
    "109.90.49.50",    # timeout
    "206.72.28.209",   # VB-M42
    "180.43.97.69",    # dead
    "133.232.94.137",  # HiSilicon
    # Additional Canon VB cams I've discovered in the past
    "158.40.218.84",   # Historical: VB-C300 in Norway
    "202.71.114.50",   # Historical
    "203.79.119.100",  # Historical
    "210.143.35.41",   # Historical
]


def expand_subnet(ip, mask=24):
    """Expand IP into all IPs in same /24 subnet."""
    parts = ip.split(".")
    if len(parts) != 4:
        return []
    prefix = ".".join(parts[:3])
    return [f"{prefix}.{i}" for i in range(1, 255)]


def probe_and_extract(ip, progress, ipapi_cache):
    """Probe a candidate IP and return cam data if VB cam found."""
    if ip in progress["scanned_ips"]:
        return None
    progress["scanned_ips"].append(ip)

    findings = probe_vb_cam(ip, port=80, use_https=False)
    if not findings["is_vb_cam"] and not findings["anon_streams"]:
        return None

    # Get geo info
    geo = geoip(ip, ipapi_cache)
    rdns = reverse_dns_lookup(ip)

    # Pick best anon stream
    if findings["anon_streams"]:
        best = findings["anon_streams"][0]
        live_url = best["url"]
        stream_type = "image" if "image" in best["content_type"] or "jpeg" in best["content_type"] else "video"
        auth_required = "False"
        http_status = 200
        content_type = best["content_type"]
        notes_parts = [f"vbviewer_id={ip}:80"]
        if findings["version"]:
            notes_parts.append(f"version={findings['version']}")
        if findings["model"]:
            notes_parts.append(f"model={findings['model']}")
        if findings["internal_ip"]:
            notes_parts.append(f"internal_ip={findings['internal_ip']}")
        if findings["auth_required"]:
            notes_parts.append(f"admin_paths={len(findings['auth_required'])}")
    else:
        # No anon stream, mark auth required
        live_url = f"http://{ip}/viewer/live/index.html?lang=en"
        stream_type = "video"
        auth_required = "True"
        http_status = 401 if findings["auth_required"] else 0
        content_type = ""
        notes_parts = [f"vbviewer_id={ip}:80", "no_anon_stream"]
        if findings["version"]:
            notes_parts.append(f"version={findings['version']}")
        if findings["model"]:
            notes_parts.append(f"model={findings['model']}")

    model = findings["model"] or detect_model_vb(findings["title"], findings["version"])
    brand = "Canon" if "VB-" in model else "Panasonic" if "BB" in model or "BL" in model else "Canon"

    desc = f"Canon VBViewer / WV-HTTP camera at {ip}. "
    desc += f"Server: {findings['server_header']}. "
    desc += f"Title: {findings['title']}. "
    if findings["version"]:
        desc += f"Version: {findings['version']}. "
    if findings["internal_ip"]:
        desc += f"Internal IP: {findings['internal_ip']} (exposed). "
    if findings["auth_required"]:
        desc += f"Admin: {len(findings['auth_required'])} auth-protected paths. "
    desc += f"Geo: {geo.get('country', '?')} / {geo.get('city', '?')}. "

    # Category based on RDNS / TLD
    category = "public"
    if rdns and (".ac.jp" in rdns or ".go.jp" in rdns or ".ed.jp" in rdns):
        category = "public"  # Japanese schools often public cams
    elif rdns and ("ne.jp" in rdns or "eonet.ne.jp" in rdns):
        category = "private"
    elif geo.get("country") in ("Japan", "South Korea"):
        category = "public"

    return {
        "url": f"http://{ip}/viewer/live/index.html?lang=en",
        "live_stream_url": live_url,
        "type": stream_type,
        "auth_required": auth_required,
        "live_status": "live" if auth_required == "False" else "unknown",
        "http_status": http_status,
        "content_type": content_type,
        "server_header": findings["server_header"],
        "page_title": findings["title"] or "Network Camera",
        "description": desc[:500],
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
        "host": ip,
        "enabled": "True",
        "category": category,
        "likely_subject": "public-space" if category == "public" else "indoor-residential",
        "confidence": "high" if auth_required == "False" else "medium",
        "notes": "; ".join(notes_parts),
    }


def scan_subnet_for_vb(seed_ip, progress, ipapi_cache):
    """Scan a /24 subnet of a seed IP for VB cams."""
    found = []
    candidates = expand_subnet(seed_ip)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(probe_and_extract, ip, progress, ipapi_cache): ip for ip in candidates}
        for fut in as_completed(futures):
            try:
                result = fut.result(timeout=15)
            except Exception:
                result = None
            if result:
                found.append(result)
    return found


def shodan_internetdb_query(ip):
    """Query Shodan InternetDB (free, no key) for IP context."""
    try:
        r = requests.get(f"https://internetdb.shodan.io/{ip}", timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def main():
    progress = load_progress()
    ipapi_cache = load_caches()
    scanned_ips = load_scanned_ips()
    progress["scanned_ips"] = list(scanned_ips)

    print(f"[VB Ingest] Starting. Cams added so far: {progress.get('cams_added', 0)}")
    print(f"[VB Ingest] Already scanned: {len(scanned_ips)} IPs")

    scans_run = set(progress.get("scans_run", []))
    next_idx = get_next_idx()

    # Phase 1: Probe seed IPs directly (high-yield, fast)
    if "seed_ips" not in scans_run:
        print(f"\n[VB Ingest] Phase 1: Probing {len(SEED_IPS)} seed IPs...")
        added = 0
        for seed_ip in SEED_IPS:
            try:
                result = probe_and_extract(seed_ip, progress, ipapi_cache)
                if result:
                    result["idx"] = next_idx
                    result["project_name"] = f"vbviewer_{seed_ip.replace('.', '_')}"
                    if append_row(result):
                        added += 1
                        next_idx += 1
                        progress["cams_added"] = progress.get("cams_added", 0) + 1
                        print(f"  Added: {seed_ip} - {result['model']} ({result.get('country', '?')})")
                time.sleep(0.5)
            except Exception as e:
                print(f"  Seed {seed_ip} error: {e}")
        save_progress(progress)
        save_ipapi_cache(ipapi_cache)
        save_scanned_ips(set(progress["scanned_ips"]))
        print(f"[VB Ingest] Phase 1 done. Added {added} cams.")
        scans_run.add("seed_ips")
        progress["scans_run"] = list(scans_run)
        save_progress(progress)

    # Phase 2: Scan /24 subnets of working seeds
    if "subnet_scan" not in scans_run:
        print(f"\n[VB Ingest] Phase 2: Scanning /24 subnets of working seeds...")
        for seed_ip in SEED_IPS[:4]:  # Limit to top 4 working seeds
            try:
                subnet_ips = expand_subnet(seed_ip)
                new_ips = [ip for ip in subnet_ips if ip not in scanned_ips and ip != seed_ip]
                print(f"  Scanning {seed_ip}/24: {len(new_ips)} IPs to probe...")
                results = scan_subnet_for_vb(seed_ip, progress, ipapi_cache)
                added = 0
                for result in results:
                    result["idx"] = next_idx
                    result["project_name"] = f"vbviewer_{result['host'].replace('.', '_')}"
                    if append_row(result):
                        added += 1
                        next_idx += 1
                        progress["cams_added"] = progress.get("cams_added", 0) + 1
                print(f"    Found {added} VB cams in {seed_ip}/24")
                save_progress(progress)
                save_ipapi_cache(ipapi_cache)
                save_scanned_ips(set(progress["scanned_ips"]))
            except Exception as e:
                print(f"  Subnet scan {seed_ip} error: {e}")
        scans_run.add("subnet_scan")
        progress["scans_run"] = list(scans_run)
        save_progress(progress)

    # Phase 3: Re-probe known CamScanner sources from past ingestion
    if "neighbor_scan" not in scans_run:
        print(f"\n[VB Ingest] Phase 3: Probing netblocks of known Canon VB cams in Shodan InternetDB...")
        # Use Shodan InternetDB to find related IPs (free, no key)
        added_total = 0
        for seed_ip in SEED_IPS[:6]:
            try:
                data = shodan_internetdb_query(seed_ip)
                if data and data.get("ports"):
                    # Try other ports this same host has open
                    for port in data.get("ports", []):
                        if port in (80, 443, 8080, 8081):
                            # Try the port
                            findings = probe_vb_cam(seed_ip, port=port, use_https=(port == 443))
                            if findings["is_vb_cam"] and findings["anon_streams"]:
                                result = probe_and_extract(seed_ip, progress, ipapi_cache)
                                if result:
                                    result["idx"] = next_idx
                                    result["project_name"] = f"vbviewer_{seed_ip.replace('.', '_')}_{port}"
                                    if append_row(result):
                                        added_total += 1
                                        next_idx += 1
                                        progress["cams_added"] = progress.get("cams_added", 0) + 1
            except Exception:
                continue
        save_progress(progress)
        save_ipapi_cache(ipapi_cache)
        save_scanned_ips(set(progress["scanned_ips"]))
        print(f"[VB Ingest] Phase 3 done. Added {added_total} additional cams.")
        scans_run.add("neighbor_scan")
        progress["scans_run"] = list(scans_run)
        save_progress(progress)

    save_progress(progress)
    save_ipapi_cache(ipapi_cache)
    save_scanned_ips(set(progress["scanned_ips"]))
    print(f"\n[VB Ingest] All phases done.")
    print(f"[VB Ingest] Total cams added this session: {progress.get('cams_added', 0)}")


if __name__ == "__main__":
    main()
