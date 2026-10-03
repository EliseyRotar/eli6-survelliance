"""Subnet scanner for VB cams - find siblings on same /24 subnet.

Strategy: for each working VB cam IP, scan the rest of the /24 subnet for more cams.
Most residential / corporate /24 nets have multiple devices; if 1 cam, there may be more.
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
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_subnet_progress.json")
IPAPI_CACHE_PATH = os.path.join(WORKDIR, "backups", "ipapi_cache.json")
SEED_IPS = [
    # Working IPs from user paste
    "61.122.58.10",      # Japan
    "202.174.60.121",    # Itayanagi - .eonet.ne.jp
    "218.42.253.97",     # Itayanagi - eonet.ne.jp (very active, 11 clients)
    "183.77.125.199",    # Itayanagi - asahi-net
    "206.72.28.209",     # Itayanagi - netins.net
    "110.4.179.61",      # Japan
    "122.249.124.12",    # Japan VB-C60
    "68.66.157.38",      # USA VB-S900F
    "82.130.141.93",     # Spain VB-M40
    "124.155.113.18",    # Japan VB-M40
    "122.250.5.56",      # Japan VB-C60
    "118.21.134.31",     # Japan VB-M600D
    "220.157.181.27",    # Japan VB-M40
    "219.111.32.223",    # Japan VB-H41
    # Already-known ASPs/ISPs that commonly host VB cams
    "133.232.94.137",    # HiSilicon (skip)
    # kaifu-intra.jp cams - same /24 likely
    "cam04.kaifu-intra.jp",
    "cam06.kaifu-intra.jp",
    "cam09.kaifu-intra.jp",
    "cam11.kaifu-intra.jp",
    "cam13.kaifu-intra.jp",
    "camera.town.owani.lg.jp",
    "camera.town.itayanagi.aomori.jp",
    "camera5.city.satsumasendai.lg.jp",
    "camera6.town.minabe.lg.jp",
    "livecamera01.town.fujikawaguchiko.lg.jp",
    "livecamera.tcs.tokogrp.co.jp",
    "live4.hi-it.jp",
    "nywebcam05.city.nayoro.hokkaido.jp",
    "kairyu-marina.aa0.netvolante.jp",
    "heart-land.aa0.netvolante.jp",
    "v075190.ppp.asahi-net.or.jp",
    "monzen.city.wajima.ishikawa.jp",
    "ooyama.town.oe.yamagata.jp",
    "yurari1.town.yuza.yamagata.jp",
    "webcam.bakio.eus",
    "www2.city.bungotakada.oita.jp",
]

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
    return {"scanned_subnets": [], "scanned_prefixes": [], "cams_added": 0}


def save_progress(p):
    try:
        os.makedirs(os.path.dirname(PROGRESS_PATH), exist_ok=True)
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


def expand_subnet_24(ip_or_host):
    """Expand a host/IP into all 254 IPs in the /24 subnet."""
    try:
        # Resolve hostname first
        try:
            ip = socket.gethostbyname(ip_or_host)
        except Exception:
            return None, None
        parts = ip.split(".")
        if len(parts) != 4:
            return None, None
        prefix = ".".join(parts[:3])
        last_octet = int(parts[3])
        candidates = [f"{prefix}.{i}" for i in range(1, 255) if i != last_octet]
        return prefix, candidates
    except Exception:
        return None, None


def probe_subnet_for_vb(ip, ipapi_cache, scanned_ips):
    """Probe one IP for VB cam."""
    if ip in scanned_ips:
        return None
    scanned_ips.add(ip)
    try:
        findings = probe_vb_cam(ip, port=80, use_https=False, timeout=3)
        if not (findings["is_vb_cam"] or findings["anon_streams"] or findings["viewer_page"]):
            return None
        # Found one
        geo = geoip(ip, ipapi_cache)
        rdns = reverse_dns(ip)
        # Build minimal row
        notes_parts = [f"vbviewer_id={ip}:80", f"subnet_scan"]
        if findings["version"]:
            notes_parts.append(f"version={findings['version']}")
        if findings["model"]:
            notes_parts.append(f"model={findings['model']}")
        if findings["internal_ip"]:
            notes_parts.append(f"internal_ip={findings['internal_ip']}")
        if rdns:
            notes_parts.append(f"rdns={rdns}")
        if geo.get("country"):
            notes_parts.append(f"country={geo['country']}")
        if findings["anon_streams"]:
            best = findings["anon_streams"][0]
            return {
                "url": f"http://{ip}/viewer/live/index.html?lang=en",
                "live_stream_url": best["url"],
                "type": "image",
                "auth_required": "False",
                "live_status": "live",
                "http_status": 200,
                "content_type": best["content_type"],
                "server_header": findings["server_header"],
                "page_title": findings["title"] or "Network Camera",
                "description": f"VB cam subnet scan: {ip} | version={findings['version']} | model={findings['model']} | rdns={rdns}",
                "brand": "Canon",
                "model": findings["model"] or "Canon VB",
                "country": geo.get("country", ""),
                "region": geo.get("regionName", ""),
                "city": geo.get("city", ""),
                "zip": geo.get("zip", ""),
                "lat": geo.get("lat", ""),
                "lon": geo.get("lon", ""),
                "geo_source": "ip-api",
                "isp": geo.get("isp", ""),
                "org": geo.get("org", ""),
                "asn": geo.get("as", ""),
                "reverse_dns": rdns,
                "host": ip,
                "category": "public" if geo.get("country") in ("Japan",) else "private",
                "likely_subject": "public-space",
                "confidence": "high",
                "notes": "; ".join(notes_parts),
            }
        else:
            # viewer-only or auth-only
            return {
                "url": f"http://{ip}/viewer/live/index.html?lang=en",
                "live_stream_url": f"http://{ip}/viewer/live/index.html?lang=en",
                "type": "video",
                "auth_required": "True" if findings["auth_required"] else "False",
                "live_status": "auth_required" if findings["auth_required"] else "unknown",
                "http_status": 401 if findings["auth_required"] else 0,
                "content_type": "",
                "server_header": findings["server_header"],
                "page_title": findings["title"] or "Network Camera",
                "description": f"VB cam subnet scan (auth): {ip} | version={findings['version']} | model={findings['model']} | rdns={rdns}",
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
                "host": ip,
                "category": "public" if geo.get("country") in ("Japan",) else "private",
                "likely_subject": "public-space",
                "confidence": "medium",
                "notes": "; ".join(notes_parts),
            }
    except Exception:
        return None


def main():
    progress = load_progress()
    ipapi_cache = load_ipapi_cache()
    scanned_ips = set(progress.get("scanned_subnets", []))
    print(f"[VB Subnet] Starting. Already scanned: {len(scanned_ips)} IPs.")
    next_idx = get_next_idx()
    print(f"[VB Subnet] CSV next idx: {next_idx}")

    subnets_done = set(progress.get("scanned_prefixes", []))
    added_total = 0

    for seed in SEED_IPS[:18]:  # Limit to top 18 seeds to keep runtime manageable
        try:
            prefix, candidates = expand_subnet_24(seed)
            if not prefix:
                print(f"  Skipping {seed} (could not resolve)")
                continue
            if prefix in subnets_done:
                print(f"  Skipping {prefix}.0/24 (already done)")
                continue
            subnets_done.add(prefix)
            progress["scanned_prefixes"] = list(subnets_done)

            # Filter out already-scanned
            new_candidates = [ip for ip in candidates if ip not in scanned_ips]
            if not new_candidates:
                continue

            print(f"\n[VB Subnet] Scanning {prefix}.0/24 from seed {seed} ({len(new_candidates)} IPs)...")
            added = 0
            with ThreadPoolExecutor(max_workers=40) as ex:
                futures = {ex.submit(probe_subnet_for_vb, ip, ipapi_cache, scanned_ips): ip for ip in new_candidates}
                for fut in as_completed(futures):
                    try:
                        result = fut.result(timeout=10)
                    except Exception:
                        result = None
                    if result:
                        result["idx"] = next_idx
                        result["project_name"] = f"vbviewer_{result['host'].replace('.', '_')}"
                        if append_row(result):
                            added += 1
                            next_idx += 1
                            added_total += 1
                            progress["cams_added"] = progress.get("cams_added", 0) + 1
                            if added <= 5:
                                print(f"    Found: {result['host']} | {result['model']} | {result.get('country', '?')} | {result['live_status']}")
            print(f"  -> {added} cams added from {prefix}.0/24")
            progress["scanned_subnets"] = list(scanned_ips)
            progress["scanned_prefixes"] = list(subnets_done)
            save_progress(progress)
            save_ipapi_cache(ipapi_cache)
        except Exception as e:
            print(f"  Subnet error for {seed}: {e}")

    save_progress(progress)
    save_ipapi_cache(ipapi_cache)
    print(f"\n[VB Subnet] Done. Total cams added this session: {added_total}")


if __name__ == "__main__":
    main()
