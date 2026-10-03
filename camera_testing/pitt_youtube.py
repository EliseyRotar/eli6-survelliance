#!/usr/bin/env python3
import urllib.request
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

# YouTube search for Hillman Library cam
print("YouTube search results:")
try:
    req = urllib.request.Request(
        "https://www.youtube.com/results?search_query=hillman+library+pitt+webcam+live",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read().decode("utf-8", errors="replace")
        vids = set(re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', data))
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}\]', data)
        print(f"  Video IDs: {len(vids)}")
        for v in list(vids)[:10]:
            print(f"    https://www.youtube.com/watch?v={v}")
        for t in titles[:10]:
            print(f"  TITLE: {t[:120]}")
except Exception as e:
    print(f"err: {e}")

print()
print("YouTube search results - Cathedral of Learning:")
try:
    req = urllib.request.Request(
        "https://www.youtube.com/results?search_query=cathedral+of+learning+pitt+webcam+live+pittsburgh",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read().decode("utf-8", errors="replace")
        vids = set(re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', data))
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}\]', data)
        print(f"  Video IDs: {len(vids)}")
        for v in list(vids)[:10]:
            print(f"    https://www.youtube.com/watch?v={v}")
        for t in titles[:10]:
            print(f"  TITLE: {t[:120]}")
except Exception as e:
    print(f"err: {e}")