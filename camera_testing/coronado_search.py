#!/usr/bin/env python3
import urllib.request
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Coronado city - look for the IBWC cam or other known cams
print("=" * 60)
print("Looking for Coronado cams in City of Coronado site")
print("=" * 60)
try:
    req = urllib.request.Request("https://www.coronado.ca.us/",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read().decode("utf-8", errors="replace")
        # Find all relevant URLs
        for pat in [r'(?i)(?:src|href)="([^"]*(?:cam|webcam|video|live)[^"]*)"',
                    r'(?i)<iframe[^>]+src="([^"]+)"',
                    r'(?i)<embed[^>]+src="([^"]+)"',
                    r'(?i)youtube\.com/embed/([^"]+)',
                    r'(?i)vimeo\.com/([^"]+)']:
            for m in re.finditer(pat, data):
                val = m.group(1) if m.groups() else m.group(0)
                print(f"  FOUND: {val[:200]}")
except Exception as e:
    print(f"err: {e}")

# Try YouTube search for "Coronado Golf Course webcam"
print()
print("=" * 60)
print("YouTube search")
print("=" * 60)
try:
    req = urllib.request.Request("https://www.youtube.com/results?search_query=coronado+golf+course+webcam+live",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read().decode("utf-8", errors="replace")
        # Find video IDs
        vids = set(re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', data))
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}\]', data)
        print(f"  Video IDs found: {len(vids)}")
        for v in list(vids)[:15]:
            print(f"    https://www.youtube.com/watch?v={v}")
        print()
        for t in titles[:10]:
            print(f"  TITLE: {t[:100]}")
except Exception as e:
    print(f"err: {e}")

# Earthcam Coronado search
print()
print("=" * 60)
print("Earthcam Coronado search")
print("=" * 60)
try:
    req = urllib.request.Request("https://www.earthcam.com/search/?query=coronado",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read().decode("utf-8", errors="replace")
        # Find cam URLs
        cams = re.findall(r'href="(/cams/[^"]+)"', data)
        for c in cams[:20]:
            print(f"  Earthcam: https://www.earthcam.com{c}")
except Exception as e:
    print(f"err: {e}")

# Try webcams.travel Coronado page
print()
print("=" * 60)
print("webcams.travel Coronado search")
print("=" * 60)
try:
    req = urllib.request.Request("https://www.webcams.travel/webcam/United-States/California/Coronado",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"  HTTP {r.status} URL: {r.geturl()}")
except Exception as e:
    print(f"err: {e}")

# YouTube direct - "Coronado live cam"
print()
print("=" * 60)
print("Try Coronado live cam channels")
print("=" * 60)
for url in [
    "https://www.youtube.com/@CoronadoGolfCourse",
    "https://www.youtube.com/@CoronadoCA",
    "https://www.youtube.com/@CoronadoChamber",
]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode("utf-8", errors="replace")
            # Find any live stream IDs
            vids = set(re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', data))
            for v in vids:
                print(f"  {url} -> https://www.youtube.com/watch?v={v}")
    except Exception as e:
        print(f"  {url} -> err {str(e)[:60]}")