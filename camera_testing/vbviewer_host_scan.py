"""Hostname-pattern scanner for VB cams.

Many VB cams are on predictable Japanese city/government domains:
- camera*.town.*.lg.jp (e.g. camera6.town.minabe.lg.jp)
- camera*.city.*.lg.jp (e.g. camera5.city.satsumasendai.lg.jp)
- cam*.kaifu-intra.jp (cam01..cam20)
- live*.hi-it.jp
- *.lg.jp (broad scan)

Strategy: enumerate subdomains from common patterns, resolve each, probe.
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
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "vbviewer_host_progress.json")
IPAPI_CACHE_PATH = os.path.join(WORKDIR, "backups", "ipapi_cache.json")

# Hostname patterns to enumerate
HOSTNAME_TEMPLATES = [
    # kaifu-intra.jp (cam01..cam50)
    *[f"cam{i:02d}.kaifu-intra.jp" for i in range(1, 51)],
    # camera[1-10].town.<name>.lg.jp  (use known ones + template)
    "camera.town.oe.yamagata.jp",
    "camera.town.oe.yamagata.jp",
    "ooyama.town.oe.yamagata.jp",
    "camera.town.itayanagi.aomori.jp",
    "camera.town.owani.lg.jp",
    "camera.town.owani.aomori.jp",
    "camera.town.yuza.yamagata.jp",
    "yurari1.town.yuza.yamagata.jp",
    "camera6.town.minabe.lg.jp",
    "camera5.city.satsumasendai.lg.jp",
    "livecamera01.town.fujikawaguchiko.lg.jp",
    "livecamera.tcs.tokogrp.co.jp",
    "live4.hi-it.jp",
    "live5.hi-it.jp",
    "live1.hi-it.jp",
    "live2.hi-it.jp",
    "live3.hi-it.jp",
    "nywebcam05.city.nayoro.hokkaido.jp",
    "nywebcam01.city.nayoro.hokkaido.jp",
    "nywebcam02.city.nayoro.hokkaido.jp",
    "nywebcam03.city.nayoro.hokkaido.jp",
    "nywebcam04.city.nayoro.hokkaido.jp",
    "nywebcam06.city.nayoro.hokkaido.jp",
    "camera5.city.satsumasendai.lg.jp",
    "camera1.city.satsumasendai.lg.jp",
    "camera2.city.satsumasendai.lg.jp",
    "camera3.city.satsumasendai.lg.jp",
    "camera4.city.satsumasendai.lg.jp",
    # Bungotakada
    "www2.city.bungotakada.oita.jp",
    "www1.city.bungotakada.oita.jp",
    "www.city.bungotakada.oita.jp",
    # netvolante
    "kairyu-marina.aa0.netvolante.jp",
    "heart-land.aa0.netvolante.jp",
    # asahi-net
    "v075190.ppp.asahi-net.or.jp",
    *[f"v{i:06d}.ppp.asahi-net.or.jp" for i in range(75000, 76000)],
    # Other patterns from paste
    "v-itcam3.uhd.edu",
    "v-itcam4.uhd.edu",
    "v-itcam1.uhd.edu",
    "v-itcam2.uhd.edu",
    "v-itcam5.uhd.edu",
    "webcam.syc.com.au",
    "boatcam.sscbc.com.au",
    "webcam.bakio.eus",
    "www3.boatnerd.com",
    "webcamtalge.southern.edu",
    # subdomain pattern: <city>.lg.jp common patterns
    "monzen.city.wajima.ishikawa.jp",
    "kankou.city.wajima.ishikawa.jp",
    # i-PRO/Hikvision/etc
    "mitaracam.city.muroran.lg.jp",
    # kaifu-intra cam 14-20
    *[f"cam{i:02d}.kaifu-intra.jp" for i in range(14, 21)],
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
    return {"scanned_hosts": [], "cams_added": 0}


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


def probe_host(host, ipapi_cache, scanned_hosts):
    """Probe one host for VB cam. Returns row dict or None."""
    if host in scanned_hosts:
        return None
    scanned_hosts.add(host)
    try:
        # Resolve hostname to IP first
        try:
            ip = socket.gethostbyname(host)
        except Exception:
            return None
        findings = probe_vb_cam(ip, port=80, use_https=False, timeout=4)
        if not findings["is_vb_cam"]:
            return None

        geo = geoip(ip, ipapi_cache)
        rdns = reverse_dns(ip)

        notes_parts = [f"vbviewer_id={ip}:80", f"host_pattern"]
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
                "description": f"VB cam pattern scan: {host} (resolved to {ip}) | version={findings['version']} | model={findings['model']} | rdns={rdns}",
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
                "host": host,
                "category": "public" if geo.get("country") in ("Japan",) else "private",
                "likely_subject": "public-space",
                "confidence": "high",
                "notes": "; ".join(notes_parts),
            }
        else:
            return {
                "url": f"http://{host}/viewer/live/index.html?lang=en",
                "live_stream_url": f"http://{host}/viewer/live/index.html?lang=en",
                "type": "video",
                "auth_required": "True" if findings["auth_required"] else "False",
                "live_status": "auth_required" if findings["auth_required"] else "unknown",
                "http_status": 401 if findings["auth_required"] else 0,
                "content_type": "",
                "server_header": findings["server_header"],
                "page_title": findings["title"] or "Network Camera",
                "description": f"VB cam pattern scan (auth): {host} (resolved to {ip}) | version={findings['version']} | model={findings['model']}",
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
    scanned_hosts = set(progress.get("scanned_hosts", []))
    print(f"[VB Host] Already scanned: {len(scanned_hosts)} hosts")
    next_idx = get_next_idx()

    added_total = 0
    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = {ex.submit(probe_host, h, ipapi_cache, scanned_hosts): h for h in HOSTNAME_TEMPLATES}
        for fut in as_completed(futures):
            host = futures[fut]
            try:
                result = fut.result(timeout=10)
            except Exception:
                result = None
            if result:
                result["idx"] = next_idx
                result["project_name"] = f"vbviewer_{host.replace('.', '_').replace(':', '_')}"
                if append_row(result):
                    added_total += 1
                    next_idx += 1
                    print(f"  [+] {host:50s} | {result['model']:20s} | {result.get('country', '?'):12s} | {result['live_status']}")
            progress["cams_added"] = added_total
            if added_total % 5 == 0:
                progress["scanned_hosts"] = list(scanned_hosts)
                save_progress(progress)
                save_ipapi_cache(ipapi_cache)

    save_progress(progress)
    save_ipapi_cache(ipapi_cache)
    print(f"\n[VB Host] Done. Added {added_total} cams from host patterns.")


if __name__ == "__main__":
    main()
