#!/usr/bin/env python3
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\pitt_webcams_wb2.html', encoding='utf-8') as f:
    h = f.read()

print("=" * 60)
print("Pitt Wayback snapshot")
print("=" * 60)

m = re.search(r'<title>(.*?)</title>', h)
if m:
    print(f"Title: {m.group(1)}")

# Strip HTML
text = re.sub(r'<script[^>]*>.*?</script>', '', h, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
print(f"\nText (first 3000):\n{text[:3000]}")

print("=" * 60)
print("All iframe/embed/video")
print("=" * 60)
for tag in ['iframe', 'embed', 'video', 'object']:
    for m in re.finditer(rf'<{tag}[^>]+(?:src|data)="([^"]+)"', h):
        print(f"  <{tag}>: {m.group(1)[:200]}")

print("=" * 60)
print("All href with cam/video")
print("=" * 60)
for m in re.finditer(r'href="([^"]+)"', h):
    href = m.group(1)
    if any(k in href.lower() for k in ['cam', 'video', 'live', 'stream', 'mjpg', 'mjpeg', 'm3u8', 'rtsp', 'rtmp', 'youtube', 'vimeo', 'iframe', '136.142']):
        print(f"  HREF: {href[:200]}")

# All 136.142.* references (Pitt's internal cam IPs)
print("=" * 60)
print("All 136.142.*.* IPs")
print("=" * 60)
ips = set(re.findall(r'136\.142\.\d+\.\d+', h))
for ip in sorted(ips):
    print(f"  {ip}")

print("=" * 60)
print("Stream-related URLs")
print("=" * 60)
for pat in [r'(?i)https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
            r'(?i)rtmp://[^\s"\'<>]+',
            r'(?i)wss?://[^\s"\'<>]+',
            r'(?i)https?://[^\s"\'<>]*\bstream\b[^\s"\'<>]*',
            r'(?i)https?://[^\s"\'<>]*\blive\b[^\s"\'<>]*']:
    for m in re.finditer(pat, h):
        print(f"  {m.group(0)[:250]}")

# Look for text-based cam mentions
print("=" * 60)
print("Cam-related text mentions")
print("=" * 60)
for m in re.finditer(r'(?i)(hillman|cathedral|webcam|live.?cam|cam.?url|streaming|live.?video).{0,200}', text):
    ctx = m.group(0)[:300]
    print(f"  {ctx}")