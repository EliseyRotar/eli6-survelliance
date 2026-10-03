"""Scrape additional Ruse webcam sources."""
import json
import os
import re
import urllib.request
import time

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT = os.path.join(WORKDIR, "dossier_ruse", "webcams")
os.makedirs(OUT, exist_ok=True)


def get(url, timeout=20):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  err {url}: {e}")
        return None


# Sources to try
SOURCES = {
    "webcamera24": "https://webcamera24.com/countries/bulgaria/ruse/",
    "eurocitycam": "https://www.eurocitycam.com/bulgaria-live-webcams-city-view-weather/ruse.html",
    "wunderground_russe": "https://www.wunderground.com/webcams/bg/ruse",
    "city_webcams": "https://city-webcams.com/bulgaria/ruse",  # retry
    "webcamtravel": "https://www.webcamgalore.com/webcam/webcam/Rouss%C3%A9.html",
    "weathercam_bg": "https://www.weathercams.bg/",
    "ruseutre": "https://www.ruseutre.bg/",
    "energo_bg": "http://www.energo-pro.bg/",  # Энерго-ПРО operates cams in Ruse
    "obshtina": "https://obshtinaruse.bg/",
    "viavarna_ruse": "https://ruse.viavarna-bg.com/",  # Via Ruse cam portal
    "ruseinfo": "https://www.ruseinfo.bg/",
    "bg_cams": "https://www.bg-cams.com/",
}


for name, url in SOURCES.items():
    print(f"\n[{name}] {url}")
    data = get(url)
    if data:
        path = os.path.join(OUT, f"{name}_raw.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data)
        print(f"  Saved {len(data)} bytes")
        # Extract cam URLs
        urls = set()
        for p in [
            r'(https?://[^\s"\'<>]+(?:\.mjpg|\.mjpeg|video\.cgi|image\.jpe?g|stream|cam\d*\.cgi)[^\s"\'<>]*)',
            r'src=["\']([^"\']+\.(?:jpg|mjpg|mjpeg))["\']',
            r'(https?://[^\s"\'<>]+cam[/?][^\s"\'<>]*)',
            r'iframe[^>]+src=["\']([^"\']+)["\']',
            r'<source[^>]+src=["\']([^"\']+)["\']',
        ]:
            for m in re.findall(p, data, re.I):
                if m.startswith('//'):
                    m = 'https:' + m
                if m.startswith('http'):
                    urls.add(m)
        print(f"  Found {len(urls)} URLs")
        if urls:
            for u in sorted(urls)[:10]:
                print(f"    {u[:100]}")
    time.sleep(1)

print("\n[DONE]")
