"""Comprehensive kaifu-intra.jp subdomain scanner.
kaifu-intra.jp has cam01..cam20 pattern with multiple subnets.
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
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_kaifu_progress.json")
IPAPI_CACHE_PATH = os.path.join(WORKDIR, "backups", "ipapi_cache.json")

# kaifu-intra.jp subdomains
KAIFU_TEMPLATES = [f"cam{i:02d}.kaifu-intra.jp" for i in range(1, 51)]
# Other predictable Japanese government cam patterns
LGJP_TEMPLATES = []
# .lg.jp gov cams - 47 prefectures, each has many cities/towns
PREFIXES = ["camera", "cam", "live", "webcam", "livecam", "livecamera", "image", "cam1", "cam2", "live1", "live2", "camera1", "camera2"]
DOMAINS = [
    "city.sapporo.hokkaido.lg.jp",
    "city.sendai.miyagi.lg.jp",
    "city.chiba.lg.jp",
    "city.yokohama.lg.jp",
    "city.kawasaki.jp",
    "city.sagamihara.kanagawa.lg.jp",
    "city.niigata.lg.jp",
    "city.shizuoka.lg.jp",
    "city.nagoya.lg.jp",
    "city.kyoto.lg.jp",
    "city.osaka.lg.jp",
    "city.kobe.lg.jp",
    "city.hiroshima.lg.jp",
    "city.fukuoka.lg.jp",
    "city.kumamoto.lg.jp",
    "city.kagoshima.lg.jp",
    "town.itayanagi.aomori.lg.jp",
    "town.yuza.yamagata.lg.jp",
    "town.oe.yamagata.lg.jp",
    "town.minabe.wakayama.lg.jp",
    "town.fujikawaguchiko.lg.jp",
    "city.muroran.hokkaido.lg.jp",
    "city.nayoro.hokkaido.lg.jp",
    "city.satsumasendai.lg.jp",
    "city.wajima.ishikawa.lg.jp",
    "city.iwade.wakayama.lg.jp",
]
for prefix in PREFIXES:
    for dom in DOMAINS:
        LGJP_TEMPLATES.append(f"{prefix}.{dom}")

ALL_HOSTS = KAIFU_TEMPLATES + LGJP_TEMPLATES

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
    return {"scanned": [], "cams_added": 0}


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


def probe_host(host, ipapi_cache, scanned):
    if host in scanned:
        return None
    scanned.add(host)
    try:
        try:
            ip = socket.gethostbyname(host)
        except Exception:
            return None
        findings = probe_vb_cam(ip, port=80, use_https=False, timeout=4)
        if not findings["is_vb_cam"]:
            return None

        geo = geoip(ip, ipapi_cache)
        rdns = reverse_dns(ip)

        notes_parts = [f"vbviewer_id={ip}:80", f"kaifu_pattern" if "kaifu" in host else f"lgjp_pattern"]
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
                "url": f"http://{host}/viewer/live/index.html?lang=en",
                "live_stream_url": best["url"],
                "type": "image",
                "auth_required": "False",
                "live_status": "live",
                "http_status": 200,
                "content_type": best["content_type"],
                "server_header": findings["server_header"],
                "page_title": findings["title"] or "Network Camera",
                "description": f"VB cam kaifu/lgjp pattern: {host} | {ip} | {findings['model']} | rdns={rdns}",
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
                "host": host,
                "category": "public",
                "likely_subject": "public-space",
                "confidence": "high",
                "notes": "; ".join(notes_parts),
            }
        elif findings["viewer_page"]:
            return {
                "url": f"http://{host}/viewer/live/index.html?lang=en",
                "live_stream_url": f"http://{host}/viewer/live/index.html?lang=en",
                "type": "video",
                "auth_required": "True" if findings["auth_required"] else "False",
                "live_status": "auth_required" if findings["auth_required"] else "unknown",
                "http_status": 401 if findings["auth_required"] else 200,
                "content_type": "",
                "server_header": findings["server_header"],
                "page_title": findings["title"] or "Network Camera",
                "description": f"VB cam kaifu/lgjp pattern (auth): {host} | {ip} | {findings['model']}",
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
                "host": host,
                "category": "public",
                "likely_subject": "public-space",
                "confidence": "medium",
                "notes": "; ".join(notes_parts),
            }
    except Exception:
        return None


def main():
    progress = load_progress()
    ipapi_cache = load_ipapi_cache()
    scanned = set(progress.get("scanned", []))
    print(f"[VB Kaifu/LGJP] Already scanned: {len(scanned)} hosts")
    next_idx = get_next_idx()
    added = 0

    with ThreadPoolExecutor(max_workers=40) as ex:
        futures = {ex.submit(probe_host, h, ipapi_cache, scanned): h for h in ALL_HOSTS}
        for fut in as_completed(futures):
            host = futures[fut]
            try:
                result = fut.result(timeout=8)
            except Exception:
                result = None
            if result:
                result["idx"] = next_idx
                result["project_name"] = f"vbviewer_{host.replace('.', '_').replace(':', '_')}"
                if append_row(result):
                    added += 1
                    next_idx += 1
                    print(f"  [+] {host:60s} | {result['model']:20s} | {result.get('country', '?'):12s} | {result['live_status']}")
            progress["cams_added"] = added
            if added % 5 == 0:
                progress["scanned"] = list(scanned)
                save_progress(progress)
                save_ipapi_cache(ipapi_cache)

    save_progress(progress)
    save_ipapi_cache(ipapi_cache)
    print(f"\n[VB Kaifu/LGJP] Done. Added {added} cams.")


if __name__ == "__main__":
    main()
