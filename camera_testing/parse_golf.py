#!/usr/bin/env python3
import re

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\golfcoronado_home.html', encoding='utf-8') as f:
    h = f.read()

print("=" * 60)
print("Search home page for webcam/video/live/iframe references")
print("=" * 60)
for pat in [r'(?i)web-?cam', r'(?i)webcam', r'(?i)\bvideo\b', r'(?i)live', r'(?i)iframe', r'(?i)youtube', r'(?i)vimeo', r'(?i)mjpg', r'(?i)mjpeg', r'(?i)hls', r'(?i)\.m3u8', r'(?i)tricaster', r'(?i)axis', r'(?i)cgi-bin', r'(?i)/cam', r'(?i)stream']:
    matches = re.findall(pat, h)
    if matches:
        print(f"Pattern {pat}: {len(matches)} matches")

print()
print("=" * 60)
print("Iframes")
print("=" * 60)
for m in re.finditer(r'<iframe[^>]+src="([^"]+)"', h):
    print(f"  {m.group(1)}")

print()
print("=" * 60)
print("Embed/object/video tags")
print("=" * 60)
for tag in ['embed', 'object', 'video']:
    for m in re.finditer(rf'<{tag}[^>]*?(?:src|data)="([^"]+)"', h):
        print(f"  <{tag}>: {m.group(1)}")

print()
print("=" * 60)
print("All links with 'cam' or 'video' or 'live'")
print("=" * 60)
for m in re.finditer(r'href="([^"]+)"', h):
    href = m.group(1)
    if any(k in href.lower() for k in ['cam', 'video', 'live', 'webcam', 'feed']):
        print(f"  {href}")

print()
print("=" * 60)
print("JS-loaded URLs (look for streaming endpoints)")
print("=" * 60)
for m in re.finditer(r'(?:src|data)=["\']([^"\']+)["\']', h):
    url = m.group(1)
    if any(k in url.lower() for k in ['cam', 'stream', 'video', 'live', '.m3u8', 'youtube', 'vimeo', 'mjpg', 'tricaster', 'axis', 'rtsp']):
        print(f"  {url}")