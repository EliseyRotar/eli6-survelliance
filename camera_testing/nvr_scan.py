"""NVR / DVR / Cloud-VMS cam suite scanner.

Detects:
- Blue Iris (default ports 81/8082)
- iSpy (default port 80 with paths /ISAPI, /etc.)
- NUUO (NUUO Network Video Recorder, port 80/8080/9000)
- Synology Surveillance Station (DSM 5000/5001/5002)
- AXIS Camera Station
- Camcloud (port 8082/80)
- ZoneMinder (port 80/8080/8443)
- Dahua NVR / DSS
- Uniview NVR
- TP-LINK NC series
- GoHawk cam server
- CPcam Cloud

For each, tries known endpoints, parses, and tries to find live streams / direct mp4 / hls.
"""
import csv
import json
import os
import random
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = random.choice([
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36',
])

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\nvr_scan_log.txt'

# Big list of residential /24 prefixes split by ASN group, derived from Shodan top-orgs.
ASN24_PREFIXES = [
    # Viettel Group (Vietnam)
    '14.160.0.0/16', '14.161.0.0/16', '14.162.0.0/16', '14.163.0.0/16',
    '14.232.0.0/16', '171.224.0.0/16', '171.228.0.0/16', '171.244.0.0/16',
    '113.160.0.0/16', '113.161.0.0/16', '113.162.0.0/16',
    # Korea Telecom
    '121.160.0.0/16', '121.161.0.0/16', '211.36.0.0/16', '218.146.0.0/16',
    '211.32.0.0/16', '211.33.0.0/16', '211.34.0.0/16',
    # Chunghwa Telecom (Taiwan)
    '36.224.0.0/16', '36.225.0.0/16', '36.226.0.0/16',
    '60.198.0.0/16', '60.199.0.0/16', '61.220.0.0/16', '61.221.0.0/16',
    # Viettel Vietnam specific
    '117.0.0.0/13', '117.4.0.0/14', '123.16.0.0/14', '125.234.0.0/15',
    # Romania (RCS & RDS)
    '86.120.0.0/13', '86.121.0.0/16', '79.114.0.0/16', '79.115.0.0/16',
    '188.24.0.0/16', '188.25.0.0/16', '188.26.0.0/16', '188.27.0.0/16',
    # Comcast US
    '24.0.0.0/12', '24.16.0.0/16', '24.32.0.0/16', '24.96.0.0/16', '24.118.0.0/16',
    '73.0.0.0/8', '76.0.0.0/12', '76.16.0.0/16', '76.24.0.0/16',
    '98.0.0.0/12', '98.96.0.0/16', '98.192.0.0/16',
    # Charter US
    '24.32.0.0/16', '24.34.0.0/16', '24.74.0.0/16', '24.94.0.0/16',
    '47.32.0.0/16', '47.34.0.0/16', '47.40.0.0/16', '47.41.0.0/16',
    '68.112.0.0/16', '68.113.0.0/16', '172.72.0.0/16', '172.73.0.0/16',
    # Verizon US (already huge in CSV)
    '71.0.0.0/12', '96.0.0.0/12', '96.64.0.0/16',
    # AT&T US (large)
    '76.0.0.0/12', '162.0.0.0/14', '172.0.0.0/14', '108.0.0.0/12',
    # T-Mobile
    '172.32.0.0/12', '172.56.0.0/12', '172.58.0.0/12',
    # Spectrum
    '47.32.0.0/16', '47.34.0.0/16', '47.35.0.0/16', '47.36.0.0/16', '47.38.0.0/16',
    # Cox Communications US
    '72.160.0.0/12', '72.165.0.0/16', '70.160.0.0/12', '70.165.0.0/16',
    # Frontier US
    '70.118.0.0/16', '108.0.0.0/16', '63.69.0.0/16',
    # Pacific Networks (Comcast)
    '68.0.0.0/12', '68.4.0.0/16', '68.8.0.0/16', '68.12.0.0/16',
]

# Cam & NVR URL probes (broad, by family)
CAM_PROBES = [
    # AXIS family (most-shodan-hit family)
    ('/axis-cgi/mjpg/video.cgi', 'axis-mjpeg'),
    ('/axis-cgi/media.cgi?container=matroska&videocodec=h264&resolution=1280x720', 'axis-h264-matroska'),
    # Blue Iris (NDVR)
    ('/mjpg/1/video.cgi', 'blueiris-mjpeg'),
    ('/mjpg/2/video.cgi', 'blueiris-mjpeg'),
    # iSpy / Agent DVR
    ('/video/mjpeg', 'ispy-mjpeg'),
    # ZoneMinder (ZMS)
    ('/cgi-bin/nph-zms', 'zoneminder'),
    # NUUO
    ('/cgi-bin/nph-zms?mode=streaming', 'nuuo'),
    ('/video.cgi?streaming=1', 'nuuo'),
    # Synology Surveillance
    ('/webapi/SurveillanceStation/camera', 'synology'),
    # AXIS Camera Station (HTTPS)
    ('/cgi-bin/acsctrl.cgi', 'axis-cs'),
    # CPcam / Generic
    ('/cgi-bin/video.cgi', 'cam-cgi'),
    # Hikvision ISAPI
    ('/ISAPI/Streaming/channels/101/httppreview', 'hikvision-h264'),
    ('/ISAPI/Streaming/channels/1/httppreview', 'hikvision-h264'),
    # Dahua
    ('/cam/realmonitor', 'dahua'),
    # TVT / Uniview
    ('/api/v1/streaming/channels', 'uniview'),
    # Mobotix
    ('/nphMotionJpeg?Resolution=640x480&Quality=Motion', 'mobotix-mjpeg'),
    # WebcamXP
    ('/cam_1.cgi', 'webcamxp'),
    ('/cam_1.mjpg', 'webcamxp-mjpg'),
    # Hipcam
    ('/web/tmpfs/mjpeg', 'hipcam-mjpeg'),
    # Generic MJPEG
    ('/video.mjpg', 'mjpeg-mjpg'),
    ('/mjpg/video.mjpg', 'mjpeg-mjpg'),
    ('/cgi-bin/mjpeg', 'mjpeg-cgi'),
    # HLS / RTMP / RTSP (just detect, not GET)
    ('/hls/stream.m3u8', 'hls'),
]

CAM_AUTH_PROBES = [
    # paths that return 401 — auth-required cams worth brute-forcing
    ('/axis-cgi/mjpg/video.cgi', 'axis'),
    ('/web/index.html#/video', 'axis'),
    ('/ISAPI/Security/sessionLogin/capabilities', 'hikvision'),
    ('/ISAPI/Security/userCheck', 'hikvision'),
    ('/web/tmpfs/snap.jpg', 'hipcam'),
    ('/ISAPI/Streaming/channels/1/picture', 'hikvision'),
]


def session():
    s = requests.Session()
    retries = Retry(total=0, backoff_factor=0.0, status_forcelist=[])
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=60, pool_maxsize=60))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=60, pool_maxsize=60))
    s.headers.update({'User-Agent': UA, 'Accept': '*/*'})
    return s


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def extract_host(c):
    m = re.match(r'(?:https?|rtsp|rtmp|mms)://([^/]+)', c)
    if not m:
        return None
    return m.group(1).lower()


def existing_hosts():
    if not os.path.exists(CSV_PATH):
        return set()
    seen = set()
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        for cell in row:
            if not cell:
                continue
            for m in re.finditer(r'(?:https?|rtsp|rtmp|mms)://([^/]+)', cell):
                h = m.group(1).lower()
                seen.add(h)
                if ':' in h:
                    seen.add(h)
    return seen


def gen_random_ips_from_prefixes(n=2000):
    import ipaddress
    ips = set()
    while len(ips) < n:
        pref = random.choice(ASN24_PREFIXES)
        try:
            net = ipaddress.ip_network(pref, strict=False)
            for _ in range(40):
                if len(ips) >= n:
                    break
                # sample inside /24 chunks
                base = ipaddress.ip_network(f'{pref.rsplit("/", 1)[0]}.0/24', strict=False)
                try:
                    idx = random.randint(0, min(base.num_addresses, 200000) - 1)
                    ips.add(str(base[idx]))
                except Exception:
                    pass
        except Exception:
            pass
    return list(ips)


def make_live_url(host, port, path, ssl=False):
    s = 'https' if ssl else 'http'
    return f'{s}://{host}:{port}{path}'


def looks_like_live(headers, body):
    ct = headers.get('Content-Type', '').lower()
    cl = headers.get('Content-Length', '-1')
    try:
        cl_n = int(cl)
    except Exception:
        cl_n = 0
    if 'multipart/x-mixed-replace' in ct:
        return 'mjpeg-multipart'
    if 'multipart/related' in ct:
        return 'mjpeg-related'
    if 'video/x-matroska' in ct:
        return 'matroska'
    if 'video/mp4' in ct:
        return 'mp4'
    if cl_n == 99999999:
        return 'mjpeg-infinite'
    if 'image/jpeg' in ct and cl_n >= 5000:
        return 'jpeg-large'
    if 'image/jpeg' in ct and cl_n >= 1500:
        return 'jpeg-frame'
    if body[:2] == b'\xff\xd8' and len(body) > 8000:
        return 'jpeg-large'
    if body[:2] == b'\xff\xd8' and len(body) > 2500:
        return 'jpeg-frame'
    return None


def main():
    sys.path.insert(0, os.path.dirname(__file__))
    import probe_lib
    import csv_writer

    s = session()
    seen_hosts = existing_hosts()
    log(f'[init] {len(seen_hosts)} existing hosts in CSV')

    # Generate candidate IPs
    candidates = []
    log('[gen] generating randomized IPs from residential ASN prefixes...')
    for ip in gen_random_ips_from_prefixes(1500):
        if ip in seen_hosts:
            continue
        for port in [80, 8080, 8000, 81, 82, 88, 8081, 8090, 8888, 554, 5000]:
            candidates.append((ip, port, False))  # (ip, port, ssl)

    # Also include HLS/RTSP probes for known cams already in CSV (already-known hosts)
    # to surface additional alt-ports
    log(f'[gen] total candidates (IP × ports): {len(candidates)}')

    n = 0
    found = 0
    auth_hits = 0

    with ThreadPoolExecutor(max_workers=80) as ex:
        futs = []
        for ip, port, ssl in candidates:
            if (ip, port) in seen_hosts:
                continue
            for path, fam in CAM_PROBES:
                futs.append(ex.submit(_probe_one, s, ip, port, ssl, path, fam, 2.0))

        # Also: probe KNOWN hosts with new paths/ports
        for h in list(seen_hosts)[:200]:
            # Skip if no IP
            if not re.match(r'^\d+\.\d+\.\d+\.\d+', h):
                continue
            for port in [8000, 8082, 8181, 9000, 8088, 80]:
                for path, fam in CAM_PROBES:
                    futs.append(ex.submit(_probe_one, s, h, port, False, path, fam, 2.0))

        log(f'[probe] {len(futs)} total probes launched')
        for fut in as_completed(futs):
            n += 1
            if n % 500 == 0:
                log(f'[progress] {n}/{len(futs)}, found {found}')
            try:
                res = fut.result(timeout=8)
            except Exception:
                continue
            if res is None:
                continue
            ip, port, path, fam, kind, url, ct = res
            # Build entry
            host = ip
            if (host, port) in seen_hosts:
                continue
            seen_hosts.add((host, port))
            try:
                geo = probe_lib.geoip(s, host)
            except Exception:
                geo = {}
            # Compose entry
            entry = {
                'host': host,
                'port': port,
                'family': fam,
                'stream_kind': kind,
                'content_type': ct,
                'live_url': url,
                'geo': geo,
            }
            try:
                idx = csv_writer.append_one(csv_writer.entry_from_probe(
                    res_dict(entry), {'source': 'nvr_asn_scan'}, geo))
                log(f'  HIT idx={idx}: {entry["family"]} {url[:100]}')
                found += 1
            except Exception as e:
                log(f'  err: {e}')


def _probe_one(s, ip, port, ssl, path, fam, timeout):
    try:
        scheme = 'https' if ssl else 'http'
        url = f'{scheme}://{ip}:{port}{path}'
        r = s.get(url, timeout=timeout, allow_redirects=False, stream=False, verify=False)
        ct = r.headers.get('Content-Type', '')
        cl = r.headers.get('Content-Length', '0')
        try:
            cl_n = int(cl)
        except Exception:
            cl_n = 0
        if r.status_code == 200:
            body = r.content[:8192]
            kind = looks_like_live(r.headers, body)
            if kind:
                return (ip, port, path, fam, kind, url, ct)
        if r.status_code == 401 and 'auth' in fam.lower():
            return (ip, port, path, fam + '-auth', 'auth', url, ct)
    except Exception:
        pass
    return None


def res_dict(entry):
    return {
        'url': entry['live_url'],
        'family': entry['family'],
        'stream_kind': entry['stream_kind'],
        'content_type': entry['content_type'],
        'content_length': 0,
        'weight': 30,
        'host': entry['host'],
        'port': entry['port'],
        'ssl': False,
        'http_status': 200,
    }


if __name__ == '__main__':
    main()
