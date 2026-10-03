#!/usr/bin/env python3
import urllib.request
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Get the live camera demos page
print("=" * 60)
print("HD Relay live camera demos")
print("=" * 60)
try:
    req = urllib.request.Request("https://www.hdrelay.com/live-camera-demos/",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read().decode("utf-8", errors="replace")
        text = re.sub(r'<script[^>]*>.*?</script>', '', data, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        print(text[:3000])
        # Find all cam IDs
        cams = set(re.findall(r'cam_[a-zA-Z0-9_]+', data))
        players = re.findall(r'player\.html\?cam=([^&"\']+)&profile=([^&"\']+)', data)
        print(f"\ncams: {cams}")
        print(f"players: {players[:5]}")
except Exception as e:
    print(f"err: {e}")

# Check Coronado city cams and Coronado hotels
print()
print("=" * 60)
print("Coronado area cams search")
print("=" * 60)
urls = [
    "https://www.coronado.ca.us/",
    "https://www.coronado.ca.us/webcams",
    "https://www.visitcoronado.com/",
    "https://webcams.travel/webcam-detail/coronado-california/",
    "https://www.earthcam.com/clients/coronado-ca/",
    "https://coronadobeach.com/webcam/",
    "https://hotelcoronado.com/webcam",
    "https://hoteldel.com/webcam",
    "https://www.loewscoronado.com/",
    "https://www.gloriettabay.com/webcam",
]
for url in urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read().decode("utf-8", errors="replace")
            cams_found = set()
            for pat in [r'(?i)mjpg[^\s"\'<>]+', r'(?i)mjpeg[^\s"\'<>]+', r'https?://[^\s"\'<>]+\.m3u8',
                        r'rtmp://[^\s"\'<>]+', r'(?i)player\.html[^\s"\'<>]+',
                        r'(?i)iframe[^>]+src="([^"]*)"', r'(?i)<embed[^>]+src="([^"]*)"']:
                for m in re.finditer(pat, data):
                    val = m.group(0) if not m.groups() else m.group(1)
                    cams_found.add(val[:150])
            print(f"  {url}")
            print(f"    HTTP {r.status} size {len(data)}")
            for c in list(cams_found)[:5]:
                print(f"    FOUND: {c}")
    except Exception as e:
        print(f"  {url} -> err {str(e)[:80]}")