#!/usr/bin/env python3
import re
import urllib.request

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"

# Get HD Relay golf course page
req = urllib.request.Request("https://www.hdrelay.com/golf-course/",
                              headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read().decode("utf-8", errors="replace")
        with open(f"{dossier}\\hdrelay_golf_full.html", "w", encoding="utf-8") as f:
            f.write(data)
        print(f"Golf course page: {len(data)} chars")

        # Find all player URLs and cam IDs
        cams = set(re.findall(r'cam_[a-zA-Z0-9_]+', data))
        print(f"cam_ IDs: {cams}")

        players = re.findall(r'player\.html\?[^\s"\'<>]+', data)
        print(f"Player URLs: {players[:5]}")

        # Find Point Loma cam ID
        pl = re.search(r'cam=cam_point_loma[^&"\']*', data)
        if pl:
            print(f"Point Loma cam: {pl.group(0)}")

        # Find demo links
        demos = re.findall(r'href="(https?://[^"]*demo[^"]*)"', data, re.IGNORECASE)
        print(f"Demo links: {demos[:5]}")

        # All player URLs from page
        for m in re.finditer(r'player\.html\?cam=([^&"\']+)&profile=([^&"\']+)', data):
            print(f"  CAM: {m.group(1)} PROFILE: {m.group(2)}")

except Exception as e:
    print(f"err: {e}")

# Try the golf resort live cam demo
print()
print("Trying various demo URLs:")
for url in [
    "https://www.hdrelay.com/demos/golf-resort-live-cam/",
    "https://www.hdrelay.com/live-cams/golf-resort-live-cam/",
    "https://www.hdrelay.com/?p=golf-resort-live-cam",
    "https://watch.hdrelay.io/player.html?cam=cam_golf_resort",
    "https://watch.hdrelay.io/?cam=golf_resort",
]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"  {url} -> HTTP {r.status} (final: {r.geturl()})")
    except Exception as e:
        print(f"  {url} -> err {e}")

# Look at the actual API endpoints that player uses
print()
print("Fetching some player assets:")
for url in [
    "https://watch.hdrelay.io/api/public/poster/cam_point_loma_1776492348923",
    "https://watch.hdrelay.io/api/public/cameras",
    "https://watch.hdrelay.io/api/public/list",
    "https://watch.hdrelay.io/api/public/cameras.json",
]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"  {url} -> HTTP {r.status} ({r.headers.get('Content-Type')})")
            print(f"    body: {r.read()[:300]}")
    except Exception as e:
        print(f"  {url} -> err {e}")