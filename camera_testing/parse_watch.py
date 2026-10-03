#!/usr/bin/env python3
import re

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\hdrelay_watch.html', encoding='utf-8') as f:
    h = f.read()

m = re.search(r'<title>(.*?)</title>', h)
if m: print(f'Title: {m.group(1)}')

# Find player URLs
print('\nPlayer URLs:')
for m in re.finditer(r'player\.html\?[^\"]+', h):
    print(f'  {m.group(0)[:200]}')

# Find camera titles
print('\nCamera titles:')
for m in re.finditer(r'<h\d[^>]*>([^<]+)</h\d>', h):
    t = m.group(1).strip()
    if t and len(t) < 100:
        print(f'  {t}')

# iframes
print('\nIframes:')
for m in re.finditer(r'<iframe[^>]+src="([^"]+)"', h):
    print(f'  {m.group(1)[:200]}')

# All watch.hdrelay.io URLs
print('\nAll watch.hdrelay.io URLs:')
for m in re.finditer(r'https://watch\.hdrelay\.io/[^\s"\']+', h):
    print(f'  {m.group(0)[:200]}')

# Find streams / m3u8 / hls / rtmp
print('\nStream endpoints:')
for pat in [r'https?://[^\s"\'<>]+\.m3u8', r'rtmp://[^\s"\'<>]+', r'hls://[^\s"\'<>]+', r'wss?://[^\s"\'<>]+', r'https?://[^\s"\'<>]*stream[^\s"\'<>]+']:
    for m in re.finditer(pat, h, re.IGNORECASE):
        print(f'  {m.group(0)[:200]}')