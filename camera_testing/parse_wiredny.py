#!/usr/bin/env python3
import re

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\wiredny_webcam.html', encoding='utf-8') as f:
    h = f.read()

print("=" * 60)
print("All SRC attributes")
print("=" * 60)
for m in re.finditer(r'src="([^"]+)"', h):
    print(f"  SRC: {m.group(1)}")

print()
print("=" * 60)
print("All HREF attributes")
print("=" * 60)
for m in re.finditer(r'href="([^"]+)"', h):
    print(f"  HREF: {m.group(1)}")

print()
print("=" * 60)
print("Video-related content")
print("=" * 60)
for pat in [r'(?i)(mjpg|mjpeg|video|stream|axis|mjpg/video\.cgi|\.m3u8|hls|rtsp|rtmp|webcam)[^\s"<>]*',
            r'(?i)<img[^>]+src="([^"]+)"',
            r'(?i)<embed[^>]+src="([^"]+)"',
            r'(?i)<object[^>]+data="([^"]+)"',
            r'(?i)url\(["\']?([^"\')\s]+)["\']?\)',
            r'(?i)window\.open\(["\']([^"\']+)["\']']:
    for m in re.finditer(pat, h):
        if hasattr(m, 'groups') and m.groups():
            print(f"  [{pat[:20]}]: {m.group(1)}")
        else:
            print(f"  [{pat[:20]}]: {m.group(0)}")