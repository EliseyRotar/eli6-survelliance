"""Aggregator / harvest library. Pulls IPs/URLs from many sources."""
import json
import random
import re
import time
import urllib.parse

import requests


# DDG HTML dorks — phase 3
DDG_QUERIES_RES = [
    '"Hipcam" webcam residential site:webcam',
    '"Hipcam" Hi3510 camera live',
    '"Hipcam" Hi3518 camera live',
    '"Hipcam" "/web/tmpfs/snap.jpg"',
    '"Hipcam" "/web/tmpfs/mjpeg"',
    '"server: Hipcam" camera',
    '"HiSilicon" Hi3510 web cam live',
    '"HiSilicon" Hi3518 web cam live',
    '"Server: Hipcam" /web/tmpfs/mjpeg',
    '"Hipcam" anonymous camera',
    'Hipcam admin admin live',
    '"Hipcam" "/web/tmpfs/snap.jpg"',
    '"Server: Hipcam" rtsp /11',
    '"Hipcam" RTSP live',
    '"hipcam" residential',
    'Hipcam Hi3510 anonymous residential',
    '"Hipcam" "no password"',
    '"Hipcam" "default" residential',
    '"hipcam cgi" hi3510',
    '"HiSilicon Hi3510" homepage',
    '"HiSilicon" home security',
    'IP camera residential private live',
    'private IP camera live stream',
    '"Server: Hipcam" 5MP',
    '"Server: Hipcam" 4MP',
    '"Server: Hipcam" H.265',
    '"Server: Hipcam" H.264',
    '"Hi3510" CGI live',
    '"Hi3518" CGI live',
    'Hipcam RTSP /11 /12',
]

DDG_QUERIES_BRANDS = [
    '"server: webcam 7" live streaming',
    '"webcam 7" -"webcam 7" site:opengamecam.com',
    '"server: webcam 5" webcam',
    '"server: webcamXP 5" streaming',
    '"/cam_1.cgi" -site:camscape -site:youtube',
    'inurl:"/cam_1.cgi" -twitter -facebook',
    'webcamXP "cam_1.cgi" live',
    '"AXIS P1447" inurl:video.cgi live',
    '"AXIS M2025" media.cgi live',
    '"Mobotix" live "/nphMotionJpeg" residential',
    'Bosch "faststream.jpg" residential',
    '"Panasonic" "/nphMotionJpeg" live',
    '"ACTi" cam live',
    '"Vivotek" live',
    '"Hikvision" pic login',
    '"Hikvision" live preview',
    'Hikvision inurl:picture channel',
    '"TP-LINK" ipcam live',
    '"D-Link" ipcam live',
    '"Lorex" ipcam live',
    '"Foscam" ipcam live',
    '"Reolink" ipcam live',
    '"Eufy" ipcam live',
    '"Amcrest" ipcam live',
    '"Annke" ipcam live',
    '"Hiseeu" ipcam live',
    '"Sannce" ipcam live',
    '"Sricam" ipcam live',
    '"Vstarcam" ipcam live',
    '"Wansview" ipcam live',
    '"Laview" ipcam live',
    '"LaView" ipcam live',
    '"GW Security" ipcam live',
    '"Zmodo" ipcam live',
    '"Uniden" ipcam live',
    '"AvertX" ipcam live',
    '"Night Owl" ipcam live',
    '"Swann" ipcam live',
    '"Geovision" ipcam live',
    '"GeoVision" ipcam live',
    '"Digital Watchdog" ipcam live',
    '"Speco" ipcam live',
    '"ONVIF" device_service',
    'ONVIF device_service residential',
    'rtsp 554 live camera',
    'rtsp public 554 anonymous',
]

DDG_QUERIES_HACK = [
    'inurl:"axis-cgi" site:webcam',
    'inurl:"cgi-bin/mjpeg" site:webcam',
    'inurl:"axis-cgi/jpg/image.cgi"',
    '"axis-cgi/media.cgi" h264',
    'inurl:webserver.htm ip',
    'HiSilicon web/tmpfs/snap',
    'inurl:-wvhttp-01- live streaming',
    '"Server: webcam 5" "User: admin"',
    '"IPCam" admin admin',
    '"Server: webcam" public live',
    '"camera5" live streaming public',
    '"server: mjpeg" cam',
    '"server: WV-HD IP"',
]


def fetch_ddg(s, queries, delay=1.0):
    urls = set()
    for q in queries:
        try:
            r = s.get('https://html.duckduckgo.com/html/', params={'q': q, 'kl': 'us-en'},
                      timeout=18)
            if r.status_code != 200:
                continue
            for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="(https?://[^"]+)"', r.text):
                u = m.group(1)
                if any(d in u for d in ('duckduckgo.com', 'duck.com', 'wikipedia.org', 'google.com',
                                         'reddit.com', 'r.jina', 'localhost', 'mozilla.org')):
                    continue
                urls.add(u)
            for m in re.finditer(r'(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?', r.text):
                urls.add(f'http://{m.group(1)}:{m.group(2) or 80}')
        except Exception as e:
            pass
        time.sleep(delay)
    return list(urls)


def fetch_insecam_index(s):
    """Hit /en/jsoncountries/ to enumerate all countries with cam count.

    Based on Camera-Hack (github.com/LiZ4rDTeam) — uses the JSON index endpoint
    that returns `{country: {name, count}}`.
    Returns dict of {cc: (name, count),...}.
    """
    out = {}
    try:
        r = s.get('http://www.insecam.org/en/jsoncountries/', timeout=10)
        if r.status_code != 200:
            return out
        try:
            data = r.json()
        except Exception:
            return out
        for cc, v in data.get('countries', {}).items():
            out[cc] = (v.get('country', cc), int(v.get('count', 0) or 0))
    except Exception:
        pass
    return out


def fetch_insecam(s, full=False):
    """Pull from insecam.org bycountry pages. With full=True hits all 100+."""
    cams = []
    pages = [
        'http://www.insecam.org/en/bycountry/US/', 'http://www.insecam.org/en/bycountry/GB/',
        'http://www.insecam.org/en/bycountry/DE/', 'http://www.insecam.org/en/bycountry/JP/',
        'http://www.insecam.org/en/bycountry/FR/', 'http://www.insecam.org/en/bycountry/IT/',
        'http://www.insecam.org/en/bycountry/ES/', 'http://www.insecam.org/en/bycountry/RU/',
        'http://www.insecam.org/en/bycountry/KR/', 'http://www.insecam.org/en/bycountry/BR/',
        'http://www.insecam.org/en/bycountry/CA/', 'http://www.insecam.org/en/bycountry/CN/',
        'http://www.insecam.org/en/bycountry/TW/', 'http://www.insecam.org/en/bycountry/MX/',
        'http://www.insecam.org/en/bycountry/AR/', 'http://www.insecam.org/en/bycountry/CO/',
        'http://www.insecam.org/en/bycountry/CL/', 'http://www.insecam.org/en/bycountry/PE/',
        'http://www.insecam.org/en/bycountry/IN/', 'http://www.insecam.org/en/bycountry/ID/',
        'http://www.insecam.org/en/bycountry/TH/', 'http://www.insecam.org/en/bycountry/VN/',
        'http://www.insecam.org/en/bycountry/PH/', 'http://www.insecam.org/en/bycountry/MY/',
        'http://www.insecam.org/en/bycountry/SG/', 'http://www.insecam.org/en/bycountry/AU/',
        'http://www.insecam.org/en/bycountry/NZ/', 'http://www.insecam.org/en/bycountry/ZA/',
        'http://www.insecam.org/en/bycountry/EG/', 'http://www.insecam.org/en/bycountry/NG/',
        'http://www.insecam.org/en/bycountry/KE/', 'http://www.insecam.org/en/bycountry/PL/',
        'http://www.insecam.org/en/bycountry/CZ/', 'http://www.insecam.org/en/bycountry/SK/',
        'http://www.insecam.org/en/bycountry/HU/', 'http://www.insecam.org/en/bycountry/RO/',
        'http://www.insecam.org/en/bycountry/BG/', 'http://www.insecam.org/en/bycountry/GR/',
        'http://www.insecam.org/en/bycountry/TR/', 'http://www.insecam.org/en/bycountry/IL/',
        'http://www.insecam.org/en/bycountry/AE/', 'http://www.insecam.org/en/bycountry/SA/',
        'http://www.insecam.org/en/bycountry/SE/', 'http://www.insecam.org/en/bycountry/NO/',
        'http://www.insecam.org/en/bycountry/FI/', 'http://www.insecam.org/en/bycountry/DK/',
        'http://www.insecam.org/en/bycountry/PT/', 'http://www.insecam.org/en/bycountry/NL/',
        'http://www.insecam.org/en/bycountry/BE/', 'http://www.insecam.org/en/bycountry/CH/',
        'http://www.insecam.org/en/bycountry/AT/',
    ]
    if full:
        pages.extend([
            'http://www.insecam.org/en/bycountry/AL/', 'http://www.insecam.org/en/bycountry/AM/',
            'http://www.insecam.org/en/bycountry/AZ/', 'http://www.insecam.org/en/bycountry/BA/',
            'http://www.insecam.org/en/bycountry/BD/', 'http://www.insecam.org/en/bycountry/BY/',
            'http://www.insecam.org/en/bycountry/CH/', 'http://www.insecam.org/en/bycountry/CY/',
            'http://www.insecam.org/en/bycountry/DZ/', 'http://www.insecam.org/en/bycountry/EC/',
            'http://www.insecam.org/en/bycountry/EE/', 'http://www.insecam.org/en/bycountry/GE/',
            'http://www.insecam.org/en/bycountry/HK/', 'http://www.insecam.org/en/bycountry/HR/',
            'http://www.insecam.org/en/bycountry/IS/', 'http://www.insecam.org/en/bycountry/JO/',
            'http://www.insecam.org/en/bycountry/KH/', 'http://www.insecam.org/en/bycountry/KW/',
            'http://www.insecam.org/en/bycountry/KZ/', 'http://www.insecam.org/en/bycountry/LB/',
            'http://www.insecam.org/en/bycountry/LK/', 'http://www.insecam.org/en/bycountry/LT/',
            'http://www.insecam.org/en/bycountry/LU/', 'http://www.insecam.org/en/bycountry/LV/',
            'http://www.insecam.org/en/bycountry/MA/', 'http://www.insecam.org/en/bycountry/MM/',
            'http://www.insecam.org/en/bycountry/MT/', 'http://www.insecam.org/en/bycountry/PA/',
            'http://www.insecam.org/en/bycountry/PK/', 'http://www.insecam.org/en/bycountry/QA/',
            'http://www.insecam.org/en/bycountry/RS/', 'http://www.insecam.org/en/bycountry/SI/',
            'http://www.insecam.org/en/bycountry/TN/', 'http://www.insecam.org/en/bycountry/UA/',
            'http://www.insecam.org/en/bycountry/UY/', 'http://www.insecam.org/en/bycountry/VE/',
        ])
    for page in pages:
        try:
            r = s.get(page, timeout=12)
            if r.status_code != 200:
                continue
            for m in re.finditer(r'<img[^>]+src="(http[^"]*viewer[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
            for m in re.finditer(r'href="(http[^"]*(?:viewer|view|stream|cam)[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
            for m in re.finditer(r'>(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?<', r.text):
                cams.append(f'http://{m.group(1)}:{m.group(2) or 80}')
        except Exception:
            pass
        time.sleep(0.8 if full else 1.5)
    return cams


# Regional insecam pages — defined for faster side-cycle scraping
INSECAM_COUNTRY_BY_REGION = {
    'EU': ['GB', 'DE', 'FR', 'IT', 'ES', 'PL', 'CZ', 'HU', 'RO', 'BG', 'GR', 'TR', 'SE', 'NO', 'FI', 'DK', 'PT', 'NL', 'BE', 'CH', 'AT', 'HR', 'RS', 'SI', 'LU', 'EE', 'LV', 'LT', 'CY', 'MT', 'IS'],
    'AM': ['US', 'CA', 'MX', 'BR', 'AR', 'CO', 'CL', 'PE', 'EC', 'UY', 'VE', 'PA', 'CR'],
    'AS': ['JP', 'KR', 'CN', 'TW', 'HK', 'IN', 'ID', 'TH', 'VN', 'PH', 'MY', 'SG', 'PK', 'BD', 'KH', 'MM', 'LK', 'KZ', 'LB', 'JO', 'KW', 'QA', 'AE', 'SA', 'AM', 'AZ', 'GE', 'IL'],
    'AF': ['ZA', 'EG', 'NG', 'KE', 'MA', 'DZ', 'TN', 'GH'],
    'OC': ['AU', 'NZ'],
}


def fetch_insecam_index_pages(s, max_pages_per_country=4, country_list=None):
    """Camera-Hack style full crawl of insecam.org via /jsoncountries/ → all countries,
    iterating multiple pages each.

    Yields IP:port URLs.

    This is by FAR the most aggressive insecam harvester — gets thousands of cam URLs
    in one run.
    """
    if country_list is None:
        idx = fetch_insecam_index(s)
        # Sort by count descending — high-yield countries first
        country_list = sorted(idx.items(), key=lambda x: -x[1][1])
    for cc, (name, count) in country_list:
        if count == 0:
            continue
        # Estimate pages needed — insecam shows ~10 cams per page.
        max_pages = min(max_pages_per_country, max(1, (count + 9) // 10))
        for p in range(max_pages):
            try:
                url = f'http://www.insecam.org/en/bycountry/{cc}/?page={p}'
                r = s.get(url, timeout=10)
                if r.status_code != 200:
                    break
                # Match IP:port patterns
                ips = re.findall(r'href\s*=\s*["\']?http://(\d+\.\d+\.\d+\.\d+):(\d+)', r.text)
                urls = [f'http://{h}:{p}' for (h, p) in ips]
                # Also raw text matches
                urls += [f'http://{m.group(1)}:{m.group(2) or 80}' for m in
                         re.finditer(r'>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::(\d{1,5}))?<', r.text)]
                # Filter to canonical http://host:port for each unique host:port
                seen = set()
                for u in urls:
                    seen.add(u)
                for u in seen:
                    yield (u, cc, name)
            except Exception:
                pass
            time.sleep(0.2)


def fetch_insecam_region(s, region):
    """Hit country pages in the given region only."""
    cams = []
    pages = [f'http://www.insecam.org/en/bycountry/{cc}/' for cc in INSECAM_COUNTRY_BY_REGION.get(region, [])]
    for page in pages:
        try:
            r = s.get(page, timeout=10)
            if r.status_code != 200:
                continue
            for m in re.finditer(r'<img[^>]+src="(http[^"]*viewer[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
            for m in re.finditer(r'href="(http[^"]*(?:viewer|view|stream|cam)[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
            for m in re.finditer(r'>(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?<', r.text):
                cams.append(f'http://{m.group(1)}:{m.group(2) or 80}')
        except Exception:
            pass
        time.sleep(1.2)
    return cams


INSECAM_BRAND_PAGES = [
    'http://www.insecam.org/en/bytype/Axis/',
    'http://www.insecam.org/en/bytype/Sony/',
    'http://www.insecam.org/en/bytype/Foscam/',
    'http://www.insecam.org/en/bytype/Bosch/',
    'http://www.insecam.org/en/bytype/Panasonic/',
    'http://www.insecam.org/en/bytype/Canon/',
    'http://www.insecam.org/en/bytype/DLink/',
    'http://www.insecam.org/en/bytype/Mobotix/',
    'http://www.insecam.org/en/bytype/TPLink/',
    'http://www.insecam.org/en/bytype/Vivotek/',
    'http://www.insecam.org/en/bytype/HiSilicon/',
    'http://www.insecam.org/en/bytype/Hikvision/',
    'http://www.insecam.org/en/bytype/AvTech/',
    'http://www.insecam.org/en/bytype/StarDot/',
    'http://www.insecam.org/en/bytype/Acti/',
    'http://www.insecam.org/en/bytag/Ptz/',
    'http://www.insecam.org/en/bytag/Architecture/',
    'http://www.insecam.org/en/bytag/Nature/',
    'http://www.insecam.org/en/bytag/Traffic/',
    'http://www.insecam.org/en/bytag/Parking/',
    'http://www.insecam.org/en/bytag/Construction/',
    'http://www.insecam.org/en/bytag/Beach/',
    'http://www.insecam.org/en/bytag/Snow/',
    'http://www.insecam.org/en/bytag/Sky/',
    'http://www.insecam.org/en/bytag/Pool/',
    'http://www.insecam.org/en/bytag/Store/',
    'http://www.insecam.org/en/bytag/Industry/',
    'http://www.insecam.org/en/bytag/Bar/',
    'http://www.insecam.org/en/bytag/Restaurant/',
]


def fetch_insecam_brands(s):
    """Insecam by-type and by-tag pages give a different selection of cams."""
    cams = []
    pages = INSECAM_BRAND_PAGES
    for page in pages:
        try:
            r = s.get(page, timeout=10)
            if r.status_code != 200:
                continue
            for m in re.finditer(r'<img[^>]+src="(http[^"]*viewer[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
            for m in re.finditer(r'href="(http[^"]*(?:viewer|view|stream|cam)[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
            for m in re.finditer(r'>(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?<', r.text):
                cams.append(f'http://{m.group(1)}:{m.group(2) or 80}')
        except Exception:
            pass
        time.sleep(0.9)
    return cams


INSECAM_CITY_PAGES = [
    'http://www.insecam.org/en/bycity/Frankfurt%20Am%20Main/',
    'http://www.insecam.org/en/bycity/London/',
    'http://www.insecam.org/en/bycity/Paris/',
    'http://www.insecam.org/en/bycity/Berlin/',
    'http://www.insecam.org/en/bycity/New%20York/',
    'http://www.insecam.org/en/bycity/Los%20Angeles/',
    'http://www.insecam.org/en/bycity/Chicago/',
    'http://www.insecam.org/en/bycity/Moscow/',
    'http://www.insecam.org/en/bycity/Tokyo/',
    'http://www.insecam.org/en/bycity/Madrid/',
    'http://www.insecam.org/en/bycity/Rome/',
    'http://www.insecam.org/en/bycity/Seoul/',
    'http://www.insecam.org/en/bycity/Singapore/',
    'http://www.insecam.org/en/bycity/Sydney/',
    'http://www.insecam.org/en/bycity/Melbourne/',
    'http://www.insecam.org/en/bycity/Auckland/',
    'http://www.insecam.org/en/bycity/Toronto/',
    'http://www.insecam.org/en/bycity/Vancouver/',
]


def fetch_internetdb_hits(s, n=200):
    """Use Shodan InternetDB to find IPs with cam-like ports open.
    For each candidate IP, query /https://internetdb.shodan.io/<ip>.
    Returns list of normalized cands.
    """
    pref = ['23.108', '24.0', '50.197', '73.128', '73.220', '75.64', '76.0', '76.96',
            '84.0', '87.139', '88.0', '89.0', '91.0', '92.0', '94.0', '95.0',
            '104.0', '108.0', '109.0', '172.0', '174.0', '176.0', '178.0',
            '188.0', '189.0', '190.0', '195.0', '198.0', '201.0', '213.0',
            '46.0', '62.0', '77.0', '78.0', '82.0', '83.0']
    ips = set()
    while len(ips) < n:
        p = random.choice(pref)
        x = random.randint(0, 254)
        y = random.randint(0, 254)
        ips.add(f'{p}.{x}.{y}')

    ips = list(ips)
    candidates = []
    cam_port_set = {80, 443, 8080, 8081, 8090, 8000, 8001, 8888, 10000, 88, 888, 8165, 10510, 10520, 81, 82, 83, 84, 85, 86, 8002, 8008, 8800, 8801, 8088, 8082, 8083, 8084, 8085, 8086, 8089, 7170, 9999, 5910, 5000}
    for ip in ips:
        try:
            r = s.get(f'https://internetdb.shodan.io/{ip}', timeout=5)
            if r.status_code != 200:
                continue
            j = r.json()
            ports = j.get('ports', []) or []
            tags = j.get('tags', []) or []
            is_cam = False
            for p in ports:
                if p in cam_port_set:
                    is_cam = True
                    break
            if not is_cam:
                for t in tags:
                    if any(k in t.lower() for k in ('cam', 'video', 'ipcam', 'stream', 'rtsp', 'webcam', 'nvr')):
                        is_cam = True
                        break
            if is_cam:
                for pp in ports:
                    if pp in cam_port_set:
                        candidates.append((ip, pp))
                        break
        except Exception:
            pass
        time.sleep(0.06)
    return [{'host': h, 'port': p, 'ssl': False, 'source': 'internetdb'} for (h, p) in candidates]


def fetch_insecam_cities(s):
    """City-level pages — single cities can have many open cams."""
    cams = []
    for page in INSECAM_CITY_PAGES:
        try:
            r = s.get(page, timeout=10)
            if r.status_code != 200:
                continue
            for m in re.finditer(r'<img[^>]+src="(http[^"]*viewer[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
            for m in re.finditer(r'href="(http[^"]*(?:viewer|view|stream|cam)[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
            for m in re.finditer(r'>(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?<', r.text):
                cams.append(f'http://{m.group(1)}:{m.group(2) or 80}')
        except Exception:
            pass
        time.sleep(0.8)
    return cams


# Other public cam indexers — opentopia replacements, EarthCam, etc.
INDEXER_PAGES = [
    'https://www.openculture.com/most_beautiful_webcams_worldwide',
    'https://www.webcam-galore.com/webcams.html',
    'https://www.webcams.travel/webcams/north-america/usa',
    'https://www.webcams.travel/webcams/europe',
    'https://www.webcams.travel/webcams/asia',
    'https://www.webcams.travel/webcams/africa',
    'https://www.webcams.travel/webcams/south-america',
    'https://www.webcams.travel/webcams/oceania',
    'https://www.worldcam.eu/webcams/',
    'https://www.skylinewebcams.com/en/webcams.html',
    'https://www.earthcam.com/network/usa',
    'https://www.earthcam.com/network/world',
    'https://www.camcloud.com/go/',  # deprecated
]


def fetch_indexers(s):
    """Pull from any listing sites that might have IP:port cams."""
    cams = []
    for page in INDEXER_PAGES:
        try:
            r = s.get(page, timeout=12, headers={'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0',
                'curl/8.4.0',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            ])})
            if r.status_code != 200:
                continue
            # Bare IP:port in text
            for m in re.finditer(r'>(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?<', r.text):
                cams.append(f'http://{m.group(1)}:{m.group(2) or 80}')
            # IP in image URLs
            for m in re.finditer(r'src="(https?://\d+\.\d+\.\d+\.\d+(?::\d+)?/[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
            # RTSP URLs
            for m in re.finditer(r'(rtsp://[a-zA-Z0-9./_:\-]+)', r.text):
                cams.append(m.group(1))
        except Exception:
            pass
        time.sleep(0.7)
    return cams


def fetch_opentopia(s, count_per_cid=30):
    """Pull from /webcam.php?cid=N"""
    urls = set()
    base_cids = [
        15, 20, 30, 44, 53, 70, 86, 97, 104, 121, 128, 139, 144, 159, 164, 183, 196,
        211, 222, 234, 247, 256, 268, 277, 286, 292, 304, 315, 326, 338,
        354, 367, 379, 392, 405, 418, 426, 437, 445, 463, 478, 491, 502,
        518, 532, 547, 559, 572, 587, 598,
        2, 5, 10, 19, 31, 41, 49, 60, 73, 88, 105, 117, 126, 142, 156, 167, 178, 197,
        211, 224, 232, 244, 257, 269, 281, 296, 309, 325, 339, 352, 367, 380, 395, 408,
        421, 437, 449, 461, 473, 488, 503,
    ]
    seen_cid = set()
    for cid in base_cids:
        seen_cid.add(cid)
    extra = []
    while len(extra) < 1000:
        extra.append(random.randint(1, 800))
    base_cids += list(seen_cid.union(extra))
    for cid in base_cids:
        try:
            r = s.get(f'https://www.opentopia.com/webcam.php?cid={cid}', timeout=10)
            if r.status_code != 200:
                continue
            for m in re.finditer(r'<img[^>]+src="(https?://[^"]+\.(?:jpg|jpeg))"', r.text, re.I):
                u = m.group(1)
                # strip .jpg suffix
                urls.add(u.rsplit('.', 1)[0])
        except Exception:
            pass
        time.sleep(0.4)
    return list(urls)


def fetch_bing_search(s, queries, delay=1.0):
    urls = set()
    for q in queries:
        try:
            r = s.get(f'https://www.bing.com/search?q={urllib.parse.quote(q)}&count=100', timeout=20,
                      headers={'Accept-Language': 'en-US,en;q=0.9'})
            if r.status_code != 200:
                continue
            for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"', r.text, re.I):
                u = m.group(1)
                if any(d in u for d in ('bing.com', 'microsoft.com', 'msn.com', 'live.com')):
                    continue
                urls.add(u)
            for m in re.finditer(r'>(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?<', r.text):
                urls.add(f'http://{m.group(1)}:{m.group(2) or 80}')
        except Exception:
            pass
        time.sleep(delay)
    return list(urls)


import random


def normalize(raw, source_label, seen_set):
    """Take raw URLs/IPs and turn into [{host, port, ssl, source}] list deduped against seen_set."""
    out = []
    seen = set()
    for u in raw:
        try:
            if not u:
                continue
            if isinstance(u, (int, float)):
                continue
            u_str = u if isinstance(u, str) else str(u)
            u_str = u_str.strip()
            if not u_str:
                continue
            # Accept "1.2.3.4:80" or "1.2.3.4" or full url
            if '://' in u_str:
                p = urllib.parse.urlparse(u_str)
                h = (p.hostname or '').lower()
                port_ = p.port or (443 if p.scheme == 'https' else 80)
                ssl_ = (p.scheme == 'https')
            elif re.match(r'^\d+\.\d+\.\d+\.\d+$', u_str):
                h = u_str
                port_ = 80
                ssl_ = False
            elif re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', u_str):
                h, port = u_str.split(':')
                h = h.strip()
                port_ = int(port)
                ssl_ = False
            else:
                continue
            if not h or '.' not in h:
                continue
            key = f'{h}:{port_}'
            if key in seen or h in seen_set:
                continue
            seen.add(key)
            out.append({'host': h, 'port': int(port_), 'ssl': ssl_, 'source': source_label})
        except Exception:
            pass
    return out
