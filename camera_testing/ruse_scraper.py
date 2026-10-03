"""Ruse webcam scraper.

Scrapes all known Ruse BG webcam aggregators + Google/DuckDuckGo for additional cams.
"""

import os
import re
import csv
import json
import time
import urllib.request
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT_DIR = os.path.join(WORKDIR, "dossier_ruse", "webcams")
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
PROGRESS = os.path.join(WORKDIR, "camera_testing", "ruse_scraper_progress.json")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
]


def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5,bg;q=0.3",
    }


def fetch(url, retries=2, timeout=15):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=get_headers())
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode('utf-8', errors='replace'), r.url
        except Exception:
            if attempt == retries - 1:
                return None, url
            time.sleep(1)


def extract_stream_urls(text, base_url=""):
    """Extract cam stream URLs from HTML."""
    urls = set()
    # Patterns for cam streams
    patterns = [
        r'src=["\']([^"\']*(?:mjpg|mjpeg|video|stream|cam|image)\.cgi[^"\']*)',
        r'src=["\']([^"\']*\.(?:mjpg|mjpeg|jpg))',
        r'href=["\']([^"\']*image\.jpe?g)',
        r'<img[^>]*src=["\']([^"\']+\.(?:jpg|jpeg))[^>]*mjpg[^>]*',
        r'(https?://[^\s"\']+(?:mjpg|mjpeg|stream|image\.jpe?g|image\.jpg|/video|/cam|/cgi)[^\s"\']*)',
        r'(rtsp://[^\s"\']+)',
        r'(https?://webcam[s]?\.[^\s"\']+/[^\s"\']*)',
        r"'(/image\.jpe?g\?[^\']+)'",
        r'"(https?://[^"]+cgi-bin/[a-zA-Z0-9_-]+\.(?:cgi|jpg))"',
        r'src=["\']([^"\']*\/cam\/[^"\']+)["\']',
    ]
    for p in patterns:
        for m in re.findall(p, text, re.I):
            url = m
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                from urllib.parse import urljoin
                url = urljoin(base_url, url)
            if url.startswith(('http://', 'https://', 'rtsp://')):
                urls.add(url)
    return list(urls)


def probe_http(url, timeout=4):
    try:
        m = re.match(r'http[s]?://([^/]+)(/.*)?', url)
        if not m:
            return None
        host_port = m.group(1)
        path = m.group(2) or '/'
        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host, host_port
            port = 80
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'GET {path} HTTP/1.0\r\nHost: {host_port}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while len(data) < 2048:
                d = sock.recv(512)
                if not d:
                    break
                data += d
        except socket.timeout:
            pass
        sock.close()
        if b'200 OK' in data[:200]:
            ct = ''
            sh = ''
            for line in data.split(b'\r\n')[:20]:
                if line.lower().startswith(b'content-type:'):
                    ct = line[12:].strip().decode('utf-8', errors='replace')
                elif line.lower().startswith(b'server:'):
                    sh = line[7:].strip().decode('utf-8', errors='replace')
                elif line == b'':
                    break
            return (200, ct, sh)
        elif b'401' in data[:200]:
            return (401, '', '')
        elif b'403' in data[:200]:
            return (403, '', '')
        return None
    except (socket.timeout, ConnectionRefusedError, OSError, Exception):
        return None


# Known Ruse webcam sources
SOURCES = [
    ("ruselive", "http://ruselive.com/main_en.htm"),
    ("ruseonline", "http://www.ruseonline.info/cam_1_en.htm"),
    ("easeweather", "https://www.easeweather.com/europe/bulgaria/ruse/webcam"),
    ("worldcam", "https://worldcam.eu/webcams/europe/bulgaria/33129-ruse-traffic"),
    ("city-webcams", "https://city-webcams.com/bulgaria/ruse"),
    ("weather-webcam", "https://weather-webcam.eu/izberi-webcam-camera/webcam-from-ruse-live-kameri-ot-ruse-na-jivo/"),
    ("spotcameras", "https://spotcameras.com/en/cams/Europe/Bulgaria/8748-Rousse-Русе--Bulgaria"),
    ("free-webcambg", "https://www.free-webcambg.com/webcams-from-ruse-live-kamerite-ot-ruse-na-jivo.html"),
    ("webcamsbg", "https://webcamsbg.com/ruse-live-webcam-camera-kamera-na-jivo-vremeto.html"),
]


def scrape_source(name, url):
    """Scrape a source, return list of stream URLs."""
    print(f"  {name} ({url})...", end="", flush=True)
    data, final_url = fetch(url)
    if not data:
        print(" FAIL (fetch error)")
        return []
    # Save raw HTML for analysis
    raw_path = os.path.join(OUT_DIR, f"{name}_raw.html")
    try:
        with open(raw_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(data)
    except Exception:
        pass

    # Extract stream URLs
    stream_urls = extract_stream_urls(data, base_url=final_url)

    # Also look for embedded players / iframes / object tags
    iframe_m = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', data, re.I)
    for url in iframe_m:
        stream_urls.extend(extract_stream_urls(url, base_url=url))

    # Look for object/embed
    obj_m = re.findall(r'<object[^>]+data=["\']([^"\']+)["\']', data, re.I)
    stream_urls.extend(obj_m)

    # Look for direct IP cams
    ips = re.findall(r'(https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}[:/][^\s"\']+)', data)
    stream_urls.extend(ips)

    print(f" {len(stream_urls)} URLs")
    return stream_urls


def probe_all(urls):
    """Probe URLs in parallel, return list of (url, status, ct, sh)."""
    results = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        for url, r in zip(urls, ex.map(probe_http, urls)):
            if r:
                status, ct, sh = r
                results.append((url, status, ct, sh))
    return results


def main():
    print(f"[Ruse Scraper] Scraping {len(SOURCES)} sources")
    progress = {"sources": {}, "live_urls": [], "found_at": {}}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS, 'r') as f:
                progress = json.load(f)
        except Exception:
            pass

    all_urls = []
    for name, url in SOURCES:
        if progress.get("sources", {}).get(name) == "done":
            print(f"  {name}: already done")
            continue
        try:
            urls = scrape_source(name, url)
        except Exception as e:
            print(f"  {name}: err {e}")
            urls = []
        all_urls.extend(urls)
        progress["sources"][name] = "done"
        progress["found_at"][name] = len(urls)
        time.sleep(2)

    # Dedupe
    unique_urls = list(set(all_urls))
    print(f"\n[Ruse Scraper] Total unique URLs: {len(unique_urls)}")
    progress["live_urls"] = unique_urls

    # Probe
    print(f"[Ruse Scraper] Probing {len(unique_urls)} URLs...")
    probed = []
    if unique_urls:
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(probe_http, u): u for u in unique_urls}
            for fut in as_completed(futures):
                url = futures[fut]
                try:
                    r = fut.result(timeout=10)
                except Exception:
                    r = None
                if r:
                    status, ct, sh = r
                    probed.append({
                        "url": url,
                        "status": status,
                        "content_type": ct,
                        "server": sh,
                    })

    print(f"[Ruse Scraper] {len(probed)} probed live/auth-required")

    # Save results
    results_path = os.path.join(OUT_DIR, "all_urls.json")
    with open(results_path, 'w') as f:
        json.dump({
            "urls": unique_urls,
            "probed": probed,
        }, f, indent=2)
    with open(PROGRESS, 'w') as f:
        json.dump(progress, f)

    # Save probed as CSV for review
    csv_path = os.path.join(OUT_DIR, "ruse_webcams.csv")
    csv.field_size_limit(2**31 - 1)
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(["url", "status", "content_type", "server", "host"])
        for r in probed:
            host_m = re.match(r'http[s]?://([^/]+)', r["url"])
            host = host_m.group(1) if host_m else ""
            w.writerow([r["url"], r["status"], r["content_type"], r["server"], host])

    # Save URLs only
    with open(os.path.join(OUT_DIR, "ruse_urls.txt"), 'w') as f:
        for r in probed:
            f.write(r["url"] + "\n")

    print(f"\n[Ruse Scraper] Saved {len(probed)} live cams to {csv_path}")


if __name__ == "__main__":
    main()
