"""Deep scrape of remaining missing sources.

Try harder to find direct cam URLs from sources that initially failed:
- fintraffic.fi - try /webcams or /cams paths
- traintrackerapp.com - try /api/railcams
- allsky7.net - try /ams39 or /cams
- 511.alberta.ca - try /cameras
- youwebcams.org - try category pages
"""
import json
import re
import sys
import time
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(line_buffering=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read(2*1024*1024).decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return -1, ''


def extract_image_urls(html):
    urls = set()
    patterns = [
        r'(https?://[^\s"\'<>]+\.jpg)',
        r'(https?://[^\s"\'<>]+\.jpeg)',
        r'(https?://[^\s"\'<>]+/mjpg/[^\s"\'<>]+)',
        r'(https?://[^\s"\'<>]+/video\.mjpg)',
        r'(https?://[^\s"\'<>]+/axis-cgi/[^\s"\'<>]+)',
        r'(https?://[^\s"\'<>]+/cgi-bin/[^\s"\'<>]+\.cgi)',
        r'(https?://[^\s"\'<>]+/cam[_\d]*\.cgi)',
        r'(https?://[^\s"\'<>]+/Streaming/[^\s"\'<>]+)',
    ]
    for p in patterns:
        for m in re.finditer(p, html, re.I):
            urls.add(m.group(1))
    return urls


# Path patterns to try
SOURCES = {
    'fintraffic': [
        'https://liikennetilanne.fintraffic.fi/webcams',
        'https://liikennetilanne.fintraffic.fi/kamerat',
        'https://liikennetilanne.fintraffic.fi/api/v1/webcams',
    ],
    'traintrackerapp': [
        'https://www.traintrackerapp.com/api/railcams',
        'https://www.traintrackerapp.com/railcams.json',
    ],
    'allsky7': [
        'https://allsky7.net/ams39',
        'https://allsky7.net/cameras',
        'https://allsky7.net/api/cameras',
    ],
    '511alberta': [
        'https://511.alberta.ca/cameras',
        'https://511.alberta.ca/api/cameras',
    ],
    'youwebcams': [
        'https://youwebcams.org/online/category/europe/',
        'https://youwebcams.org/online/category/asia/',
        'https://youwebcams.org/online/',
        'https://youwebcams.org/online/webcams/',
    ],
    'webcamerasgr': [
        'https://www.webcameras.gr/',
    ],
    'webcamromania': [
        'https://webcamromania.ro/',
    ],
    'cxtvlive': [
        'https://cxtvlive.com/',
    ],
    'myairportcams': [
        'https://myairportcams.com/',
    ],
    'itsansan': [
        'https://its.ansan.go.kr/',
    ],
}


def main():
    found = {}
    for source, urls in SOURCES.items():
        print(f'\n[{source}]', flush=True)
        for url in urls:
            status, html = fetch(url, timeout=10)
            print(f'  {url} -> {status}', flush=True)
            if status == 200:
                imgs = extract_image_urls(html)
                if imgs:
                    found[url] = list(imgs)
                    print(f'    found {len(imgs)} image URLs', flush=True)
                    for img in list(imgs)[:3]:
                        print(f'      {img[:80]}', flush=True)
            time.sleep(0.5)

    with open('tv_deep_scrape.json', 'w') as f:
        json.dump(found, f, indent=2)
    print(f'\nSaved {len(found)} scrape results to tv_deep_scrape.json', flush=True)


if __name__ == '__main__':
    main()
