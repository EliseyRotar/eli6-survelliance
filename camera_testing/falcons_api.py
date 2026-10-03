#!/usr/bin/env python3
import re
import urllib.request
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Explore.org feeds API
try:
    req = urllib.request.Request(
        "https://explore.org/api/feeds/cathedral-of-learning-pittsburgh-falcons",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
        print(json.dumps(data, indent=2)[:3000])
except Exception as e:
    print(f"err: {e}")

# Explore.org livecam group falcons
print()
print("Falcons group feed:")
try:
    req = urllib.request.Request(
        "https://explore.org/api/livecam-groups/falcons",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
        print(json.dumps(data, indent=2)[:2000])
except Exception as e:
    print(f"err: {e}")

# Try Wayback for any captured falconcam stream
print()
print("Wayback for falconcam stream:")
import subprocess
r = subprocess.run(
    ["curl", "-s", "--max-time", "20", "-A", "Mozilla/5.0",
     "https://web.archive.org/cdx/search/cdx?url=explore.org/livecams/falcons/*&output=json&limit=10"],
    capture_output=True, text=True)
print(r.stdout[:2000])

# Direct HLS probe - explore.org typically uses m3u8 from cloudfront/akamai
print()
print("Direct probe - explore.org livestream URLs:")
for url in [
    "https://explore.org/livecams/falcons/cathedral-of-learning-pittsburgh-falcons",
    "https://explore.org/livecams/player/cathedral-of-learning-pittsburgh-falcons",
    "https://explore.org/api/feeds/cathedral-of-learning-pittsburgh-falcons",
    "https://explore.org/api/v1/live-cams/cathedral-of-learning-pittsburgh-falcons",
]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode("utf-8", errors="replace")
            print(f"  {url}")
            print(f"    HTTP {r.status} size {len(data)}")
            # find m3u8 or stream
            for pat in [r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
                        r'https?://[^\s"\'<>]*\bhls\b[^\s"\'<>]*',
                        r'https?://[^\s"\'<>]*\bstream\b[^\s"\'<>]*',
                        r'https?://[^\s"\'<>]*\bplayer[^\s"\'<>]*']:
                for m in re.finditer(pat, data):
                    print(f"    URL: {m.group(0)[:200]}")
    except Exception as e:
        print(f"  {url} -> err {str(e)[:60]}")