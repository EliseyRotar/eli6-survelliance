"""Use Shodan InternetDB (free, no key) to find sibling services/ports on each cam IP.
Plus enumerate more predictable subnet patterns.
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vbviewer_probe import probe_vb_cam

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV_PATH = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_intel_progress.json")
IPAPI_CACHE_PATH = os.path.join(WORKDIR, "backups", "ipapi_cache.json")

# Load VB cams from CSV to use as seeds
def load_existing_vb():
    csv.field_size_limit(2**31 - 1)
    rows = []
    if not os.path.exists(CSV_PATH):
        return rows
    with open(CSV_PATH, "r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r, None)
        if not header:
            return rows
        for row in r:
            if len(row) < len(header):
                row += [""] * (len(header) - len(row))
            rows.append(dict(zip(header, row)))
    return rows


def resolve_to_ip(host):
    """Resolve host or IP to IP."""
    if not host:
        return None
    try:
        # If it's already an IP, return it
        socket.inet_aton(host)
        return host
    except Exception:
        # Resolve hostname
        try:
            return socket.gethostbyname(host)
        except Exception:
            return None


def query_internetdb(ip):
    """Query Shodan InternetDB for free (no API key needed)."""
    try:
        r = requests.get(f"https://internetdb.shodan.io/{ip}", timeout=10)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return {"ip": ip, "ports": [], "tags": [], "vulns": []}
    except Exception:
        pass
    return {}


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"scanned_ips": [], "sibling_cams": 0}


def save_progress(p):
    try:
        os.makedirs(os.path.dirname(PROGRESS_PATH), exist_ok=True)
        with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(p, f)
    except Exception:
        pass


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
                w.writerow(list(row_dict.keys()))
        except Exception:
            return False
    try:
        with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            row = [str(row_dict.get(k, "")) for k in list(row_dict.keys()) if k != "idx" or True]
            # Get keys from header
            row = []
            for k in row_dict.keys():
                v = row_dict[k]
                if isinstance(v, str) and "\n" in v:
                    v = v.replace("\n", " ").replace("\r", " ")
                row.append(str(v) if v is not None else "")
            w.writerow(row)
        return True
    except Exception as e:
        return False


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


def probe_vb_at_host_port(host, port, ipapi_cache, scanned):
    """Probe a specific host:port for VB cam."""
    key = f"{host}:{port}"
    if key in scanned:
        return None
    scanned.add(key)
    findings = probe_vb_cam(host, port=port, use_https=False, timeout=4)
    if not findings["is_vb_cam"]:
        return None

    ip = resolve_to_ip(host) or host
    geo = geoip(ip, ipapi_cache)
    rdns = reverse_dns(ip)

    notes_parts = [f"vbviewer_id={ip}:{port}", f"internetdb_scan"]
    if findings["version"]:
        notes_parts.append(f"version={findings['version']}")
    if findings["model"]:
        notes_parts.append(f"model={findings['model']}")
    if findings["internal_ip"]:
        notes_parts.append(f"internal_ip={findings['internal_ip']}")

    if findings["anon_streams"]:
        best = findings["anon_streams"][0]
        return {
            "idx": 0,  # Will be set by caller
            "project_name": f"vbviewer_{host.replace('.', '_').replace(':', '_')}",
            "url": f"http://{host}:{port}/viewer/live/index.html?lang=en",
            "live_stream_url": best["url"],
            "type": "image",
            "auth_required": "False",
            "auth_user": "",
            "auth_pass": "",
            "enabled": "True",
            "live_status": "live",
            "http_status": 200,
            "content_type": best["content_type"],
            "server_header": findings["server_header"],
            "page_title": findings["title"] or "Network Camera",
            "description": f"VB cam from InternetDB scan: {host}:{port} | model={findings['model']} | version={findings['version']}",
            "category": "public" if geo.get("country") in ("Japan",) else "private",
            "likely_subject": "public-space",
            "brand": "Canon",
            "model": findings["model"] or "Canon VB",
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
            "confidence": "high",
            "notes": "; ".join(notes_parts),
            "csv_id": "",
        }
    return None


def main():
    progress = load_progress()
    ipapi_cache = {}
    if os.path.exists(IPAPI_CACHE_PATH):
        try:
            with open(IPAPI_CACHE_PATH, "r", encoding="utf-8") as f:
                ipapi_cache = json.load(f) or {}
        except Exception:
            pass

    scanned = set(progress.get("scanned_ips", []))
    print(f"[VB InternetDB] Already scanned: {len(scanned)} host:port combos")
    next_idx = get_next_idx()

    # Load existing VB cams from CSV as seeds
    rows = load_existing_vb()
    print(f"[VB InternetDB] Loaded {len(rows)} existing VB cams from CSV")

    seed_ips = set()
    for row in rows:
        host = row.get("host", "")
        ip = resolve_to_ip(host)
        if ip:
            seed_ips.add(ip)

    print(f"[VB InternetDB] {len(seed_ips)} unique IPs to query InternetDB")
    added = 0

    # For each IP, query InternetDB
    for seed_ip in list(seed_ips)[:60]:  # Limit to avoid rate limits
        if seed_ip in scanned:
            continue
        scanned.add(seed_ip)
        try:
            data = query_internetdb(seed_ip)
            if not data:
                continue
            ports = data.get("ports", [])
            # InternetDB returns ports this IP has open - probe alternate ports too
            for port in ports:
                if port in (80, 443, 8080, 8081, 5000, 554):
                    # Try the port
                    scheme = "https" if port == 443 else "http"
                    try:
                        result = probe_vb_at_host_port(seed_ip, port, ipapi_cache, scanned)
                    except Exception:
                        result = None
                    if result:
                        result["idx"] = next_idx
                        if append_row(result):
                            added += 1
                            next_idx += 1
                            print(f"  [+] {seed_ip}:{port} | {result['model']} | {result.get('country', '?')} | {result['live_status']}")
            time.sleep(1.5)  # Rate limit
        except Exception as e:
            pass

    # Save
    save_ipapi_cache = None
    try:
        with open(IPAPI_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(ipapi_cache, f)
    except Exception:
        pass
    progress["scanned_ips"] = list(scanned)
    progress["sibling_cams"] = added
    save_progress(progress)
    print(f"\n[VB InternetDB] Done. Added {added} cams from InternetDB scan.")


if __name__ == "__main__":
    main()
