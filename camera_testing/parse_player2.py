#!/usr/bin/env python3
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\hdrelay_point_loma.html', encoding='utf-8') as f:
    h = f.read()

# Strip scripts/styles
text = re.sub(r'<script[^>]*>.*?</script>', '', h, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
print('Page text (first 2000):')
print(text[:2000])
print('\n---\n')

# Streams
print('Stream URLs:')
for pat in [r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
            r'rtmp://[^\s"\'<>]+',
            r'wss?://[^\s"\'<>]+',
            r'https?://[^\s"\'<>]+/(?:hls|stream|live|edge)[^\s"\'<>]*']:
    for m in re.finditer(pat, h, re.IGNORECASE):
        print(f'  {m.group(0)[:300]}')

# Camera params
print('\nQuery params:')
for m in re.finditer(r'\b(?:cam|profile|sig|exp)=([^&\s"\'<>]+)', h):
    print(f'  {m.group(0)[:200]}')

# All scripts
print('\nAll script srcs:')
for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', h):
    print(f'  {m.group(1)[:200]}')

# Any watch.hdrelay.io URLs
print('\nAll watch.hdrelay.io refs:')
for m in re.finditer(r'https?://watch\.hdrelay\.io/[^\s"\'<>]+', h):
    print(f'  {m.group(0)[:200]}')

# Search JSON config blocks for camera/stream details
print('\nJSON blocks with cam:')
for m in re.finditer(r'\{[^{}]*(?:cam|profile|sig|exp|stream|live|video)[^{}]*\}', h, re.IGNORECASE):
    print(f'  {m.group(0)[:300]}')