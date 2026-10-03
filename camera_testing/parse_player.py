#!/usr/bin/env python3
import re

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\hdrelay_point_loma.html', encoding='utf-8') as f:
    h = f.read()

# Strip scripts/styles
text = re.sub(r'<script[^>]*>.*?</script>', '', h, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
print('Page text:')
print(text[:3000])
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

# All src/href in this page
print('\nAll src/href:')
for m in re.finditer(r'(?:src|href|data)=["\']([^"\']+)["\']', h):
    u = m.group(1)
    if any(k in u.lower() for k in ['.js', '.m3u8', 'stream', 'live', 'cam', 'player', 'api', 'edge']):
        print(f'  {u[:200]}')

# All scripts
print('\nAll script srcs:')
for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', h):
    print(f'  {m.group(1)[:200]}')