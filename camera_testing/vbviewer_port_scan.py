"""Try ports 80, 81, 443, 5000, 554, 8080, 8081, 8888, 9000, 10000 on each VB cam IP.
InternetDB shows other open ports - if any of those host VB cams on the same IP, add them.
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
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_portscan_progress.json")
IPAPI_CACHE_PATH = os.path.join(WORKDIR, "backups", "ipapi_cache.json")

PROBE_PORTS = [80, 81, 443, 554, 5000, 5001, 8080, 8081, 8443, 8888, 9000, 10000]


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


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"scanned": [], "cams_added": 0}


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


def probe_port(host, port, ipapi_cache, scanned):
    """Probe one host:port for VB cam."""
    key = f"{host}:{port}"
    if key in scanned:
        return None
    scanned.add(key)
    use_https = port in (443, 8443, 5000)
    findings = probe_vb_cam(host, port=port, use_https=use_https, timeout=4)
    if not findings["is_vb_cam"]:
        return None

    ip = resolve_to_ip(host) or host
    geo = geoip(ip, ipapi_cache)
    rdns = reverse_dns(ip)

    notes_parts = [f"vbviewer_id={ip}:{port}", f"port_scan"]
    if findings["version"]:
        notes_parts.append(f"version={findings['version']}")
    if findings["model"]:
        notes_parts.append(f"model={findings['model']}")
    if findings["internal_ip"]:
        notes_parts.append(f"internal_ip={findings['internal_ip']}")
    if rdns and rdns != host:
        notes_parts.append(f"rdns={rdns}")

    if findings["anon_streams"]:
        best = findings["anon_streams"][0]
        return {
            "idx": 0,
            "project_name": f"vbviewer_{host.replace('.', '_').replace(':', '_')}_{port}",
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
            "description": f"VB cam port scan: {host}:{port} | model={findings['model']} | version={findings['version']}",
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

    scanned = set(progress.get("scanned", []))
    print(f"[VB PortScan] Already scanned: {len(scanned)} host:port combos")
    next_idx = get_next_idx()

    rows = load_existing_vb()
    seed_ips = set()
    for row in rows:
        host = row.get("host", "")
        ip = resolve_to_ip(host)
        if ip:
            seed_ips.add(ip)
    print(f"[VB PortScan] {len(seed_ips)} unique IPs to scan across {len(PROBE_PORTS)} ports")

    added = 0
    tasks = []
    for ip in seed_ips:
        for port in PROBE_PORTS:
            tasks.append((ip, port))

    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = {ex.submit(probe_port, h, p, ipapi_cache, scanned): (h, p) for h, p in tasks}
        for fut in as_completed(futures):
            try:
                result = fut.result(timeout=10)
            except Exception:
                result = None
            if result:
                result["idx"] = next_idx
                if append_row(result):
                    added += 1
                    next_idx += 1
                    print(f"  [+] {result['host']}:{futures[fut][1]} | {result['model']} | {result.get('country', '?')}")
            if added % 5 == 0:
                progress["scanned"] = list(scanned)
                progress["cams_added"] = added
                save_progress(progress)
                try:
                    with open(IPAPI_CACHE_PATH, "w", encoding="utf-8") as f:
                        json.dump(ipapi_cache, f)
                except Exception:
                    pass

    progress["scanned"] = list(scanned)
    progress["cams_added"] = added
    save_progress(progress)
    try:
        with open(IPAPI_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(ipapi_cache, f)
    except Exception:
        pass
    print(f"\n[VB PortScan] Done. Added {added} cams from port scan.")


if __name__ == "__main__":
    main()
