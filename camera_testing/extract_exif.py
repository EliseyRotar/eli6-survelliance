"""Tier 3: EXIF GPS extractor from JPEG frames.

For each cam with image/MJPEG/M3U8 stream:
- Fetch first ~256 KB of stream
- Find JPEG SOI marker (FF D8 FF)
- Parse EXIF GPS IFD
- If lat/lon present and valid, replace IP-traced coords

EXIF GPS IFD structure:
- Tag 0x0001 GPSLatitudeRef ('N' or 'S')
- Tag 0x0002 GPSLatitude (3 rationals: degrees, minutes, seconds)
- Tag 0x0003 GPSLongitudeRef ('E' or 'W')
- Tag 0x0004 GPSLongitude (3 rationals)
"""
import csv
import io
import os
import re
import struct
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\extract_exif_log.txt'


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=200))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=200))
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    })
    return s


def find_jpeg_soi_in_stream(data):
    """Find JPEG SOI (FF D8 FF) marker in data and return (start, end) or None."""
    pos = 0
    while pos < len(data) - 3:
        if data[pos] == 0xFF and data[pos+1] == 0xD8 and data[pos+2] == 0xFF:
            # Find EOI (FF D9) after this SOI
            eoi = data.find(b'\xff\xd9', pos+3)
            if eoi > 0:
                return data[pos:eoi+2]
            # If no EOI, take 50KB from SOI
            return data[pos:pos+50_000]
        pos += 1
    return None


def parse_exif_gps(jpeg_bytes):
    """Parse EXIF GPS from JPEG bytes. Returns (lat, lon) or (None, None)."""
    if not jpeg_bytes or len(jpeg_bytes) < 4:
        return None, None
    if jpeg_bytes[:2] != b'\xff\xd8':
        return None, None
    if jpeg_bytes[2] != 0xFF:
        return None, None
    # APP1 marker FF E1
    if jpeg_bytes[3] != 0xE1:
        return None, None

    try:
        # APP1 length (2 bytes big-endian) — but it's the segment length including itself
        seg_len = struct.unpack('>H', jpeg_bytes[4:6])[0]
        if seg_len < 8:
            return None, None
        app1 = jpeg_bytes[6:4+seg_len]
        if not app1.startswith(b'Exif\x00\x00'):
            return None, None
        tiff_start = 8  # skip 'Exif\x00\x00'
        tiff = jpeg_bytes[4+tiff_start:]

        # TIFF header: II*\0 (little-endian) or MM\0* (big-endian)
        if tiff[:2] == b'II':
            endian = '<'
        elif tiff[:2] == b'MM':
            endian = '>'
        else:
            return None, None
        # Magic 42
        magic = struct.unpack(endian + 'H', tiff[2:4])[0]
        if magic != 42:
            return None, None
        ifd0_offset = struct.unpack(endian + 'I', tiff[4:8])[0]
        ifd0 = tiff[ifd0_offset:]
        # Parse IFD0 to find GPS IFD offset
        num_entries = struct.unpack(endian + 'H', ifd0[:2])[0]
        if num_entries > 100:
            return None, None
        gps_offset = None
        for i in range(num_entries):
            entry = ifd0[2 + i*12:2 + (i+1)*12]
            tag = struct.unpack(endian + 'H', entry[:2])[0]
            if tag == 0x8825:  # GPSInfo IFD pointer
                gps_offset = struct.unpack(endian + 'I', entry[8:12])[0]
                break
        if gps_offset is None:
            return None, None
        gps_ifd = tiff[gps_offset:]
        num_gps = struct.unpack(endian + 'H', gps_ifd[:2])[0]
        if num_gps > 50:
            return None, None
        lat_ref = lon_ref = ''
        lat_rats = lon_rats = None
        for i in range(num_gps):
            e = gps_ifd[2 + i*12:2 + (i+1)*12]
            tag = struct.unpack(endian + 'H', e[:2])[0]
            t = struct.unpack(endian + 'H', e[2:4])[0]
            cnt = struct.unpack(endian + 'I', e[4:8])[0]
            voff = e[8:12]
            if tag == 0x0001 and t == 2:  # GPSLatitudeRef ASCII
                lat_ref = voff.decode('ascii', errors='ignore').rstrip('\0')
            elif tag == 0x0002 and t == 5:  # GPSLatitude RATIONAL x3
                lat_rats = struct.unpack(endian + 'III', voff) if False else [
                    rational_from(tiff, voff, endian),
                    rational_from(tiff, struct.pack(endian + 'I', struct.unpack(endian + 'I', voff)[0]+8), endian),
                    rational_from(tiff, struct.pack(endian + 'I', struct.unpack(endian + 'I', voff)[0]+16), endian),
                ]
            elif tag == 0x0003 and t == 2:  # GPSLongitudeRef
                lon_ref = voff.decode('ascii', errors='ignore').rstrip('\0')
            elif tag == 0x0004 and t == 5:  # GPSLongitude RATIONAL x3
                lon_rats = [
                    rational_from(tiff, voff, endian),
                    rational_from(tiff, struct.pack(endian + 'I', struct.unpack(endian + 'I', voff)[0]+8), endian),
                    rational_from(tiff, struct.pack(endian + 'I', struct.unpack(endian + 'I', voff)[0]+16), endian),
                ]
        if lat_rats and lon_rats and all(lat_rats) and all(lon_rats):
            lat = lat_rats[0] + lat_rats[1]/60 + lat_rats[2]/3600
            lon = lon_rats[0] + lon_rats[1]/60 + lon_rats[2]/3600
            if lat_ref == 'S':
                lat = -lat
            if lon_ref == 'W':
                lon = -lon
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
    except Exception:
        pass
    return None, None


def rational_from(tiff, offset_bytes, endian):
    """Read a RATIONAL (num, denom) at given offset in TIFF data."""
    off = struct.unpack(endian + 'I', offset_bytes)[0]
    if off + 8 > len(tiff):
        return 0
    num, denom = struct.unpack(endian + 'II', tiff[off:off+8])
    if denom == 0:
        return 0
    return num / denom


def fetch_first_frame(s, url, max_bytes=256*1024):
    """Fetch first chunk of stream. Try to get JPEG."""
    try:
        r = s.get(url, timeout=5, allow_redirects=True, verify=False, stream=True)
        if r.status_code >= 400:
            return None
        chunks = []
        got = 0
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                chunks.append(chunk)
                got += len(chunk)
                if got >= max_bytes:
                    break
        r.close()
        return b''.join(chunks)
    except Exception:
        return None


def process_row(s, row):
    """Process one row. Returns (lat, lon) or None."""
    stream_url = row[3]
    if not stream_url:
        return None
    # Skip pure HLS / RTSP
    ul = stream_url.lower()
    if ul.startswith('rtsp://') or ul.endswith('.m3u8') or ul.endswith('.m3u'):
        return None
    if '.mp4' in ul:
        return None
    # Skip if already tier3
    notes = row[33] if len(row) > 33 else ''
    if 'tier3:exif' in notes:
        return None

    data = fetch_first_frame(s, stream_url)
    if not data:
        return None
    jpeg = find_jpeg_soi_in_stream(data)
    if not jpeg:
        return None
    lat, lon = parse_exif_gps(jpeg)
    if lat is not None and lon is not None:
        return lat, lon
    return None


def main():
    log('[init] starting EXIF extractor (Tier 3)')
    s = session()

    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    log(f'[init] {len(rows)-1} rows')

    cols = {h: i for i, h in enumerate(header)}
    LAT = cols['lat']; LON = cols['lon']
    CGEO = cols.get('geo_source', None)

    # Target: insecam_dump + full-reprobe first (most likely to be MJPEG cams)
    # Also: argus-v2 and others that have image streams
    targets = []
    for i, r in enumerate(rows[1:], start=1):
        if len(r) <= 33:
            continue
        notes = r[33]
        src = notes.split('source=')[1].split(',')[0].split(';')[0] if 'source=' in notes else ''
        # Only process MJPEG/image cams, not HLS
        url = (r[3] or '').lower()
        if '.m3u' in url or '.mp4' in url or url.startswith('rtsp://'):
            continue
        # Skip if already tier3
        if CGEO is not None and len(r) > CGEO and r[CGEO].startswith('tier3'):
            continue
        # Only public source types mostly
        if src in ('argus-v2', 'live_env2', 'live_env', 'argus', 'windy_com', 'insecam_dump', 'full-reprobe', 'insecam', 'insecam-EU', 'insecam-AS', 'insecam_2019', 'camera_hack'):
            targets.append((i, r))
    log(f'[plan] {len(targets)} rows to scan for EXIF')

    updated = 0
    done = 0
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(process_row, s, t[1]): t for t in targets}
        for f in as_completed(futures):
            done += 1
            try:
                result = f.result()
            except Exception:
                continue
            idx = futures[f][0]
            if result:
                lat, lon = result
                r = rows[idx]
                r[LAT] = str(lat)
                r[LON] = str(lon)
                if CGEO is not None:
                    r[CGEO] = 'tier3:exif-gps'
                updated += 1
                log(f'  EXIF GPS: idx={idx} -> {lat:.4f}, {lon:.4f} | url={r[3][:60]}')
            if done % 100 == 0:
                log(f'  progress {done}/{len(targets)} updated={updated}')
                tmp = CSV_PATH + '.tmp'
                with open(tmp, 'w', encoding='utf-8', newline='') as f:
                    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                    for rr in rows:
                        w.writerow(rr)
                os.replace(tmp, CSV_PATH)
    log(f'[done] updated {updated} rows with EXIF GPS')
    tmp = CSV_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow(r)
    os.replace(tmp, CSV_PATH)


if __name__ == '__main__':
    main()
