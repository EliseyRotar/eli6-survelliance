"""Fast Insecam bulk scraper v3.

Scrapes insecam /bytype/{brand}/, /byrating/, /mapcity/.
"""

import os
import csv
import re
import json
import time
import random
import urllib.request
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV_PATH = os.path.join(WORKDIR, "controllable_Webcams.csv")
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "insecam_bulk_progress.json")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]


def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}


def fetch_page(url, retries=2):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=get_headers())
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode(errors='replace')
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(1)


def scrape_pages(base_url, max_pages=80):
    """Scrape all pages of a URL pattern. Stops when page returns no cams."""
    found = set()
    for page in range(1, max_pages + 1):
        url = f'{base_url}?page={page}'
        data = fetch_page(url)
        if not data:
            break
        urls = re.findall(r'(http[s]?://[^"\s<>]+:[0-9]+/[^"\s<>]+)', data)
        if not urls:
            break
        found.update(urls)
        time.sleep(0.3)
    return list(found)


def probe_http(url, timeout=4):
    try:
        m = re.match(r'http[s]?://([^/]+)(/.*)?', url)
        if not m:
            return (None, None, None)
        host_port = m.group(1)
        path = m.group(2) or '/'
        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host = host_port
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
        elif b'401' in data[:200] or b'Unauthorized' in data[:500]:
            return (401, '', '')
        elif b'403' in data[:200]:
            return (403, '', '')
        return (None, None, None)
    except (socket.timeout, ConnectionRefusedError, OSError):
        return (None, None, None)
    except Exception:
        return (None, None, None)


def load_existing_urls():
    urls = set()
    if not os.path.exists(CSV_PATH):
        return urls
    try:
        csv.field_size_limit(2**31 - 1)
        with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
            for row in csv.DictReader(f):
                if row.get('url'):
                    urls.add(row['url'])
                if row.get('live_stream_url'):
                    urls.add(row['live_stream_url'])
    except Exception as e:
        print(f"[Insecam] Error loading CSV: {e}")
    return urls


def append_to_csv(rows):
    """Atomically append rows to master CSV with retry on lock conflict."""
    if not rows:
        return 0

    MAX_RETRIES = 15
    LOCK_PATH = CSV_PATH + ".lock"

    for attempt in range(MAX_RETRIES):
        try:
            lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(lock_fd, str(os.getpid()).encode())
            os.close(lock_fd)
        except FileExistsError:
            time.sleep(2 + random.uniform(0, 3))
            continue

        try:
            csv.field_size_limit(2**31 - 1)
            existing_rows = []
            header = None
            with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
                header = reader.fieldnames

            if not header:
                if os.path.exists(LOCK_PATH):
                    os.remove(LOCK_PATH)
                return 0

            start_idx = len(existing_rows) + 1
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            appended = 0
            for row in rows:
                if not row.get('url'):
                    continue
                new_row = {k: '' for k in header}
                new_row['idx'] = str(start_idx)
                new_row['url'] = row.get('url', '')
                new_row['live_stream_url'] = row.get('url', '')
                new_row['project_name'] = 'insecam'
                new_row['type'] = 'video' if 'mjpg' in row.get('url', '') or 'mjpeg' in row.get('url', '') else 'image'
                new_row['enabled'] = '1'
                new_row['live_status'] = row.get('live_status', 'unknown')
                new_row['http_status'] = str(row.get('http_status', ''))
                new_row['content_type'] = row.get('content_type', '')
                new_row['server_header'] = row.get('server_header', '')
                new_row['brand'] = row.get('brand', 'insecam')
                new_row['category'] = 'public_cam'
                new_row['confidence'] = '0.5'
                new_row['notes'] = f"insecam bulk scrape {timestamp}"
                new_row['csv_id'] = f"INSECAM-{int(time.time())}-{start_idx}"
                new_row['host'] = row.get('host', '')
                existing_rows.append(new_row)
                start_idx += 1
                appended += 1

            tmp = CSV_PATH + ".tmp"
            for i in range(5):
                try:
                    with open(tmp, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                        writer.writeheader()
                        writer.writerows(existing_rows)
                    os.replace(tmp, CSV_PATH)
                    break
                except PermissionError:
                    time.sleep(2 + random.uniform(0, 3))
            if os.path.exists(tmp):
                os.remove(tmp)
            if os.path.exists(LOCK_PATH):
                os.remove(LOCK_PATH)
            return appended
        except Exception as e:
            if os.path.exists(LOCK_PATH):
                try:
                    os.remove(LOCK_PATH)
                except Exception:
                    pass
            print(f"[Insecam] CSV append attempt {attempt} err: {e}")
            time.sleep(3)
    return 0


def process_source(name, base_url, max_pages, scraped, existing_urls, progress_path, append_csv_fn):
    """Process a single source (brand or rating)."""
    if scraped.get(name) == "done":
        return 0, 0

    print(f"  Scraping {name}...", end="", flush=True)
    urls = scrape_pages(base_url, max_pages)
    new_urls = [u for u in urls if u not in existing_urls]
    dupes = len(urls) - len(new_urls)
    print(f" {len(urls)} URLs ({len(new_urls)} new, {dupes} dupes)", end="", flush=True)

    pending = []
    live_count = 0
    total_probed = 0
    if new_urls:
        with ThreadPoolExecutor(max_workers=30) as ex:
            for r in ex.map(probe_http, new_urls):
                total_probed += 1
                if r:
                    status, ct, sh = r
                    if status == 200 or status == 401:
                        live_count += 1
                        host_m = re.match(r'http[s]?://([^/]+)', new_urls[total_probed - 1])
                        host = host_m.group(1) if host_m else ''
                        pending.append({
                            'url': new_urls[total_probed - 1],
                            'host': host,
                            'live_status': 'live' if status == 200 else 'auth_required',
                            'http_status': status,
                            'content_type': ct,
                            'server_header': sh,
                            'brand': name.lower(),
                        })

    scraped[name] = "done"
    print(f" | {live_count} live", flush=True)

    if pending:
        added = append_csv_fn(pending)
        print(f"    [CSV] +{added} cams")
    return live_count, len(urls)


def main():
    BRANDS = [
        "Streamer", "Canon", "DLink-DCS-932", "ChannelVision", "Axis", "Axis2", "AxisMkII",
        "Panasonic", "WYM", "TPLink", "WIFICam", "GK7205", "Sony-CS3", "DLink", "Linksys",
        "Vivotek", "Android-IPWebcam", "Bosch", "Vije", "Toshiba", "Yawcam", "BlueIris",
        "Hi3516", "Megapixel", "Sony", "Defeway", "Motion",
        "AVTech", "Cisco", "Mobotix", "IQInvision", "AirLive", "Pixord", "Arecont",
        "Grandstream", "Foscam", "Hikvision", "Dahua", "Acti",
    ]

    print(f"[Insecam Bulk v3] Scraping {len(BRANDS)} brands + byrating")
    progress_path = PROGRESS_PATH
    scraped = {}
    if os.path.exists(progress_path):
        try:
            with open(progress_path, "r") as f:
                p = json.load(f)
                scraped = p.get("scraped", {})
        except Exception:
            pass

    existing_urls = load_existing_urls()
    print(f"[Insecam Bulk v3] {len(existing_urls):,} existing URLs for dedup")

    total_live = 0
    total_new = 0
    start_time = time.time()

    # Process brands
    for brand_idx, brand in enumerate(BRANDS):
        if scraped.get(f"brand_{brand}") == "done":
            print(f"  [{brand_idx+1}/{len(BRANDS)}] {brand}: already done", flush=True)
            continue

        elapsed = time.time() - start_time
        rate = brand_idx / max(elapsed, 1)
        eta = (len(BRANDS) - brand_idx - 1) / max(rate, 0.01)
        print(f"  [{brand_idx+1}/{len(BRANDS)}] {brand}... (ETA {eta:.0f}s)", end="", flush=True)

        urls = scrape_pages(f'http://www.insecam.org/en/bytype/{brand}/', 80)
        new_urls = [u for u in urls if u not in existing_urls]
        scraped[f"brand_{brand}"] = "done"

        pending = []
        live_count = 0
        probed = 0
        if new_urls:
            with ThreadPoolExecutor(max_workers=30) as ex:
                for r in ex.map(probe_http, new_urls):
                    probed += 1
                    if r:
                        status, ct, sh = r
                        if status == 200 or status == 401:
                            live_count += 1
                            host_m = re.match(r'http[s]?://([^/]+)', new_urls[probed - 1])
                            host = host_m.group(1) if host_m else ''
                            pending.append({
                                'url': new_urls[probed - 1],
                                'host': host,
                                'live_status': 'live' if status == 200 else 'auth_required',
                                'http_status': status,
                                'content_type': ct,
                                'server_header': sh,
                                'brand': brand.lower(),
                            })

        total_live += live_count
        print(f" {len(urls)} URLs ({len(new_urls)} new), {live_count} live", flush=True)

        # Save CSV
        if pending:
            added = append_to_csv(pending)
            total_new += added
            pending = []
            with open(progress_path, "w") as f:
                json.dump({"scraped": scraped, "total_live": total_live, "total_new": total_new}, f)

    # Process byrating (255 pages × 6 cams = ~1500 cams)
    print(f"\n[Insecam Bulk v3] Scraping byrating...")
    for page in range(1, 260):
        if scraped.get(f"byrating_{page}") == "done":
            continue
        urls = scrape_pages(f'http://www.insecam.org/en/byrating/', 1)
        if not urls:
            break
        # Actually, we need to fetch each page explicitly
        url = f'http://www.insecam.org/en/byrating/?page={page}'
        data = fetch_page(url)
        if not data:
            break
        page_urls = re.findall(r'(http[s]?://[^"\s<>]+:[0-9]+/[^"\s<>]+)', data)
        page_urls = list(set(page_urls))
        new_urls = [u for u in page_urls if u not in existing_urls]
        scraped[f"byrating_{page}"] = "done"

        pending = []
        live_count = 0
        if new_urls:
            with ThreadPoolExecutor(max_workers=30) as ex:
                for r in ex.map(probe_http, new_urls):
                    if r:
                        status, ct, sh = r
                        if status == 200 or status == 401:
                            live_count += 1
                            host_m = re.match(r'http[s]?://([^/]+)', new_urls[0])
                            host = host_m.group(1) if host_m else ''

        print(f"  Rating p{page}: {len(page_urls)} URLs ({len(new_urls)} new), live={live_count}", end="", flush=True)

        # Quick probe and add
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(probe_http, u): u for u in new_urls}
            for fut in as_completed(futures):
                url = futures[fut]
                try:
                    r = fut.result(timeout=10)
                except Exception:
                    r = None
                if r:
                    status, ct, sh = r
                    if status == 200 or status == 401:
                        host_m = re.match(r'http[s]?://([^/]+)', url)
                        host = host_m.group(1) if host_m else ''
                        pending.append({
                            'url': url,
                            'host': host,
                            'live_status': 'live' if status == 200 else 'auth_required',
                            'http_status': status,
                            'content_type': ct,
                            'server_header': sh,
                            'brand': 'insecam_top',
                        })
        print(f" saved={len(pending)}")
        total_live += len(pending)
        if pending:
            added = append_to_csv(pending)
            total_new += added
            with open(progress_path, "w") as f:
                json.dump({"scraped": scraped, "total_live": total_live, "total_new": total_new}, f)
        time.sleep(0.5)

    # Process mapcity
    print(f"\n[Insecam Bulk v3] Scraping mapcity...")
    city_data = fetch_page('http://www.insecam.org/en/mapcity/')
    if city_data:
        city_links = re.findall(r'/en/mapcity/([^/"\?]+)/', city_data)
        city_links = [c for c in set(city_links) if c and not c.startswith('?') and 'mapcity' not in c.lower()]
        city_links = city_links[:50]
        print(f"  Found {len(city_links)} cities")
        for city_idx, city in enumerate(city_links):
            if scraped.get(f"city_{city}") == "done":
                continue
            urls = scrape_pages(f'http://www.insecam.org/en/mapcity/{city}/', 30)
            new_urls = [u for u in urls if u not in existing_urls]
            scraped[f"city_{city}"] = "done"

            pending = []
            live_count = 0
            if new_urls:
                with ThreadPoolExecutor(max_workers=20) as ex:
                    futures = {ex.submit(probe_http, u): u for u in new_urls}
                    for fut in as_completed(futures):
                        url = futures[fut]
                        try:
                            r = fut.result(timeout=10)
                        except Exception:
                            r = None
                        if r:
                            status, ct, sh = r
                            if status == 200 or status == 401:
                                live_count += 1
                                host_m = re.match(r'http[s]?://([^/]+)', url)
                                host = host_m.group(1) if host_m else ''
                                pending.append({
                                    'url': url,
                                    'host': host,
                                    'live_status': 'live' if status == 200 else 'auth_required',
                                    'http_status': status,
                                    'content_type': ct,
                                    'server_header': sh,
                                    'brand': 'insecam_city',
                                })

            print(f"  [{city_idx+1}/{len(city_links)}] {city}: {len(urls)} URLs ({len(new_urls)} new), {live_count} live")
            total_live += live_count
            if pending:
                added = append_to_csv(pending)
                total_new += added

    print(f"\n[Insecam Bulk v3] Done! Total live: {total_live}, added to CSV: {total_new}")


if __name__ == "__main__":
    main()
