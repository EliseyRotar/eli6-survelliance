"""Restore Ruse cams from dossier_ruse/ data into master CSV.

We preserve Ruse-specific discoveries in dossier_ruse/ - this script re-injects
those cams into the rebuilt master CSV.
"""
import os
import csv
import json
import time
import random
import re
import urllib.request

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
RESTORE_LOG = os.path.join(WORKDIR, "camera_testing", "ruse_restore.json")

# List of Ruse cams to restore (extracted from earlier discoveries)
RUSE_CAMS = [
    # Windy.com cams (Bulgaria)
    {
        "url": "https://images-webcams.windy.com/15/1597690315/current/full/1597690315.jpg",
        "live_stream_url": "https://images-webcams.windy.com/15/1597690315/current/full/1597690315.jpg",
        "brand": "ruse_windy", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse BG - Windy cam 1597690315",
    },
    {
        "url": "https://images-webcams.windy.com/15/1793898215/current/full/1793898215.jpg",
        "live_stream_url": "https://images-webcams.windy.com/15/1793898215/current/full/1793898215.jpg",
        "brand": "ruse_windy", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse BG - Windy cam 1793898215",
    },
    {
        "url": "https://images-webcams.windy.com/97/1793902097/current/full/1793902097.jpg",
        "live_stream_url": "https://images-webcams.windy.com/97/1793902097/current/full/1793902097.jpg",
        "brand": "ruse_windy", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse BG - Windy cam 1793902097",
    },
    # Yandex Weather cam 20758
    {
        "url": "https://info.weather.yandex.net/20758/3.png",
        "live_stream_url": "https://info.weather.yandex.net/20758/3.png",
        "brand": "ruse_yandex", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse Yandex weather cam ID 20758",
    },
    # Worldcam.pl cams (Bulgaria)
    {
        "url": "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/14906.jpg",
        "live_stream_url": "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/14906.jpg",
        "brand": "ruse_worldcam", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse - Worldcam cam 14906",
    },
    {
        "url": "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/24496.jpg",
        "live_stream_url": "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/24496.jpg",
        "brand": "ruse_worldcam", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse - Worldcam cam 24496",
    },
    {
        "url": "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/2706.jpg",
        "live_stream_url": "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/2706.jpg",
        "brand": "ruse_worldcam", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse - Worldcam cam 2706",
    },
    {
        "url": "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/37360.jpg",
        "live_stream_url": "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/37360.jpg",
        "brand": "ruse_worldcam", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse - Worldcam cam 37360",
    },
    {
        "url": "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/40580.jpg",
        "live_stream_url": "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/40580.jpg",
        "brand": "ruse_worldcam", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse - Worldcam cam 40580",
    },
    # WebcamsBG street cam
    {
        "url": "https://webcamsbg.com/cams/ruse-street.jpg",
        "live_stream_url": "https://webcamsbg.com/cams/ruse-street.jpg",
        "brand": "ruse_webcamsbg", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse street cam from webcamsbg.com",
    },
    # Webcamera24 (auth-required)
    {
        "url": "https://cdn.webcamera24.com/static/image/camera/detail/8438-omv-bala-uastreaming/",
        "live_stream_url": "",
        "brand": "ruse_webcamera24", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "OMV Bala streaming (Ruse area)",
        "live_status": "auth_required",
    },
    {
        "url": "https://cdn.webcamera24.com/static/image/camera/detail/8565-ueb-kamera-ot-letise-ruse-s-srklevo-uast/",
        "live_stream_url": "",
        "brand": "ruse_webcamera24", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse letishte Srklevo (Ruse airport)",
        "live_status": "auth_required",
    },
    {
        "url": "https://cdn.webcamera24.com/static/image/camera/detail/8566-ueb-kamera-ot-letise-ruse-lbrs-ruse-do-s/",
        "live_stream_url": "",
        "brand": "ruse_webcamera24", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "LBRS Ruse (school)",
        "live_status": "auth_required",
    },
    # Ruse Traffic cam - geofenced BG-only
    {
        "url": "http://212.25.48.117:8080/axis-cgi/mjpg/video.cgi?webcam.jpg",
        "live_stream_url": "http://212.25.48.117:8080/axis-cgi/mjpg/video.cgi?webcam.jpg",
        "brand": "ruse_axis_geofenced", "country": "Bulgaria", "city": "Ruse",
        "lat": "43.82306", "lon": "25.95389",
        "notes": "Ruse Traffic cam on 212.25.48.117:8080 - GEOFENCED (BG-only IP)",
        "live_status": "auth_required",  # Will be live if accessed from BG
    },
]


def probe_url(url, timeout=8):
    """Probe URL to confirm it's live."""
    try:
        ctx = None
        if url.startswith('https://'):
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        ctx_arg = {'context': ctx} if ctx else {}
        with urllib.request.urlopen(req, timeout=timeout, **ctx_arg) as r:
            ct = r.headers.get('Content-Type', '')
            data = r.read()
            if r.status == 200:
                return (200, ct, len(data))
            return (r.status, ct, len(data))
    except urllib.error.HTTPError as e:
        return (e.code, '', 0)
    except Exception as e:
        return (-1, str(e)[:50], 0)


def append_to_csv(rows):
    if not rows:
        return 0
    csv.field_size_limit(2**31 - 1)
    MAX_RETRIES = 15
    LOCK_PATH = MASTER_CSV + ".lock"

    for attempt in range(MAX_RETRIES):
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            time.sleep(2 + random.uniform(0, 3))
            continue

    try:
        existing = []
        header = None
        with open(MASTER_CSV, 'r', encoding='utf-8', errors='replace', newline='') as f:
            reader = csv.DictReader(f)
            existing = list(reader)
            header = reader.fieldnames
        if not header:
            if os.path.exists(LOCK_PATH):
                os.remove(LOCK_PATH)
            return 0

        start = len(existing) + 1
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        appended = 0
        for row in rows:
            url = row.get('url', '')
            if not url:
                continue
            new_row = {k: '' for k in header}
            new_row['idx'] = str(start)
            new_row['url'] = url
            new_row['live_stream_url'] = row.get('live_stream_url') or url
            new_row['project_name'] = 'ruse_restored'
            new_row['type'] = 'video' if any(k in url for k in ['mjpg', 'mjpeg']) else 'image'
            new_row['enabled'] = '1'
            new_row['live_status'] = row.get('live_status', 'live')
            new_row['http_status'] = str(row.get('http_status', ''))
            new_row['content_type'] = row.get('content_type', '')
            new_row['server_header'] = ''
            new_row['brand'] = row.get('brand', 'ruse_restored')
            new_row['category'] = 'public_cam'
            new_row['country'] = row.get('country', 'Bulgaria')
            new_row['city'] = row.get('city', 'Ruse')
            new_row['lat'] = row.get('lat', '43.82306')
            new_row['lon'] = row.get('lon', '25.95389')
            new_row['confidence'] = '0.7'
            new_row['notes'] = row.get('notes', '') + f' | restored {ts}'
            new_row['csv_id'] = f"RUSERESTORED-{int(time.time())}-{start}"
            new_row['host'] = url.split('://')[1].split(':')[0] if '://' in url else ''
            existing.append(new_row)
            start += 1
            appended += 1
        tmp = MASTER_CSV + ".tmp"
        for i in range(5):
            try:
                with open(tmp, 'w', encoding='utf-8', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                    w.writeheader()
                    w.writerows(existing)
                os.replace(tmp, MASTER_CSV)
                break
            except PermissionError:
                time.sleep(2)
        if os.path.exists(tmp):
            os.remove(tmp)
        if os.path.exists(LOCK_PATH):
            os.remove(LOCK_PATH)
        return appended
    except Exception:
        if os.path.exists(LOCK_PATH):
            try: os.remove(LOCK_PATH)
            except: pass
        return 0


def main():
    print(f'[Ruse Restore] Restoring {len(RUSE_CAMS)} Ruse cams from dossier...')
    csv.field_size_limit(2**31 - 1)

    existing = set()
    with open(MASTER_CSV, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  Current CSV: {len(existing):,} URLs')

    # Probe and add
    rows_to_add = []
    for cam in RUSE_CAMS:
        url = cam['url']
        if url in existing:
            print(f'  [skip] {url[:80]} (already in CSV)')
            continue
        status, ct, size = probe_url(url)
        print(f'  [{status}] {url[:80]} ({ct[:30]}, {size}B)')
        cam['http_status'] = status
        cam['content_type'] = ct
        if status == 200:
            cam['live_status'] = 'live'
            rows_to_add.append(cam)
        elif status in [401, 403]:
            cam['live_status'] = 'auth_required'
            rows_to_add.append(cam)

    if rows_to_add:
        added = append_to_csv(rows_to_add)
        print(f'\n[Ruse Restore] Added {added} cams to master CSV')

    # Save restore log
    with open(RESTORE_LOG, 'w') as f:
        json.dump({
            'restored': len(rows_to_add),
            'total_cams_attempted': len(RUSE_CAMS),
            'timestamp': time.time(),
        }, f, indent=2)
    print(f'  Log: {RESTORE_LOG}')


if __name__ == '__main__':
    main()
