#!/usr/bin/env python3
import urllib.request
import re
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Try Bunyan CDN with video.m3u8
urls_to_try = [
    "https://media.explore.org/cathedral-of-learning-pittsburgh-falcons/video.m3u8",
    "https://media.explore.org/cathedral-of-learning-pittsburgh-falcons/index.m3u8",
    "https://live-explore.b-cdn.net/cathedral-of-learning-pittsburgh-falcons/video.m3u8",
    "https://live-explore.b-cdn.net/cathedral-of-learning-pittsburgh-falcons/index.m3u8",
    # Try CloudFront pattern
    "https://d2xppk4jbl34j8.cloudfront.net/cathedral-of-learning-pittsburgh-falcons/playlist.m3u8",
    "https://d3v4phh8lxxr.cloudfront.net/cathedral-of-learning-pittsburgh-falcons/playlist.m3u8",
    "https://d2v8d39xz4w3.cloudfront.net/cathedral-of-learning-pittsburgh-falcons/playlist.m3u8",
    "https://explore-org.b-cdn.net/cathedral-of-learning-pittsburgh-falcons/playlist.m3u8",
]

for url in urls_to_try:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode("utf-8", errors="replace")
            print(f"OK {url}")
            print(f"  HTTP {r.status} size {len(data)}")
            print(f"  data: {data[:300]}")
    except urllib.error.HTTPError as e:
        print(f"  {e.code} {url}")
    except Exception as e:
        print(f"  ERR {url}: {str(e)[:80]}")

# Let's look at the actual HTML to find stream URL - search for any videoUrl / hls / m3u8
print()
print("Reading explore page HTML...")
try:
    req = urllib.request.Request(
        "https://explore.org/livecams/falcons/cathedral-of-learning-pittsburgh-falcons",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read().decode("utf-8", errors="replace")
        # find iframe or video
        for m in re.finditer(r'(?:src|data-url)="([^"]+)"', data):
            url = m.group(1)
            if 'b-cdn' in url or 'm3u8' in url or 'cloudfront' in url:
                print(f"  STREAM URL: {url}")
        # Find next.js data
        if "__NEXT_DATA__" in data:
            m = re.search(r'__NEXT_DATA__[^>]*>([^<]+)', data)
            if m:
                try:
                    nd = json.loads(m.group(1))
                    print(f"  NEXT_DATA keys: {list(nd.keys())}")
                    # Recursive search for m3u8
                    def find_streams(obj, depth=0):
                        if depth > 8: return
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if isinstance(v, str) and ('m3u8' in v or 'cloudfront' in v or 'b-cdn' in v):
                                    print(f"    FOUND [{k}]: {v[:300]}")
                                find_streams(v, depth+1)
                        elif isinstance(obj, list):
                            for item in obj:
                                find_streams(item, depth+1)
                    find_streams(nd)
                except Exception as e:
                    print(f"  parse err: {e}")
except Exception as e:
    print(f"err: {e}")