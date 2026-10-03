#!/usr/bin/env python3
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\pitt_webcams.html', encoding='utf-8') as f:
    h = f.read()

print("=" * 60)
print("Pitt webcams page")
print("=" * 60)

m = re.search(r'<title>(.*?)</title>', h)
if m:
    print(f"Title: {m.group(1)}")

text = re.sub(r'<script[^>]*>.*?</script>', '', h, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
print(f"\nText (first 3000):\n{text[:3000]}")

print("=" * 60)
print("All iframes / embeds / videos")
print("=" * 60)
for tag in ['iframe', 'embed', 'video', 'object']:
    for m in re.finditer(rf'<{tag}[^>]+(?:src|data)="([^"]+)"', h):
        print(f"  <{tag}>: {m.group(1)[:200]}")

print("=" * 60)
print("All SRC attributes")
print("=" * 60)
for m in re.finditer(r'src="([^"]+)"', h):
    print(f"  SRC: {m.group(1)[:200]}")

print("=" * 60)
print("All HREF attributes (filtered)")
print("=" * 60)
for m in re.finditer(r'href="([^"]+)"', h):
    href = m.group(1)
    if any(k in href.lower() for k in ['cam', 'video', 'live', 'stream', 'mjpg', 'mjpeg', 'm3u8', 'rtsp', 'rtmp', 'youtube', 'vimeo', 'iframe']):
        print(f"  HREF: {href[:200]}")

print("=" * 60)
print("Stream-related URLs")
print("=" * 60)
for pat in [r'(?i)https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
            r'(?i)rtmp://[^\s"\'<>]+',
            r'(?i)wss?://[^\s"\'<>]+',
            r'(?i)https?://[^\s"\'<>]*\bmjpg\b[^\s"\'<>]*',
            r'(?i)https?://[^\s"\'<>]*\bmjpeg\b[^\s"\'<>]*',
            r'(?i)https?://[^\s"\'<>]*\bvideo\b[^\s"\'<>]*',
            r'(?i)https?://[^\s"\'<>]*\bstream\b[^\s"\'<>]*']:
    for m in re.finditer(pat, h):
        print(f"  STREAM: {m.group(0)[:250]}")

print("=" * 60)
print("Common webcam host patterns")
print("=" * 60)
for m in re.finditer(r'https?://[^\s"\'<>]+', h):
    url = m.group(0)
    if any(k in url.lower() for k in ['axis.com', 'tricaster', 'newtek', 'earthcam', 'webcam', 'cctv', 'camera', 'sony', 'panasonic', 'camserver', 'streaming', 'stream', 'wowza', 'wowz', 'hls', 'akamai', 'cloudfront', 'videojs', 'jwplayer', 'flowplayer', 'jwplatform']):
        print(f"  {url[:200]}")