#!/usr/bin/env python3
import re
import urllib.request
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Load the golf page text and search for cam links
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\hdrelay_golf_full.html', encoding='utf-8') as f:
    h = f.read()

# Strip HTML
text = re.sub(r'<script[^>]*>.*?</script>', '', h, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()

# Find any camera-related text
print("Golf cam mentions:")
for m in re.finditer(r'(?i)(live[\s\-]?cam|live[\s\-]?stream|golf[\s\-]?course|demo)', text):
    ctx_start = max(0, m.start()-50)
    ctx_end = min(len(text), m.end()+100)
    ctx = text[ctx_start:ctx_end].strip()
    print(f"  ...{ctx}...")

# Try common demo URLs
print("\nProbing common demo URLs:")
demo_urls = [
    "https://www.hdrelay.com/live-camera-demos/",
    "https://www.hdrelay.com/live-camera-demos",
    "https://www.hdrelay.com/point-loma-live-camera/",
    "https://www.hdrelay.com/industries/golf-course-camera/",
    "https://www.hdrelay.com/golf-resort-live-cam/",
    "https://www.hdrelay.com/golf-course-camera/",
]
for url in demo_urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"  {url} -> HTTP {r.status}")
            data = r.read().decode("utf-8", errors="replace")
            # Find cam IDs
            cams = set(re.findall(r'cam_[a-zA-Z0-9_]+', data))
            players = re.findall(r'player\.html\?cam=([^&"\']+)&profile=([^&"\']+)', data)
            if cams:
                print(f"    cam IDs: {cams}")
            if players:
                print(f"    Player URLs: {players[:3]}")
    except Exception as e:
        print(f"  {url} -> err {str(e)[:60]}")

# Now check Coronado specifically with different search terms
print("\nSearch HD Relay for Coronado via site search:")
try:
    req = urllib.request.Request("https://www.hdrelay.com/?s=coronado+golf",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read().decode("utf-8", errors="replace")
        # Find any cam-related links
        print(f"  Page: {len(data)} chars")
        for m in re.finditer(r'(?i)(coronado|sandiego|chula[\s\-]?vista|california)', data):
            ctx_start = max(0, m.start()-100)
            ctx_end = min(len(data), m.end()+100)
            ctx = re.sub(r'<[^>]+>', ' ', data[ctx_start:ctx_end]).strip()
            print(f"    ...{ctx[:250]}...")
except Exception as e:
    print(f"  err: {e}")