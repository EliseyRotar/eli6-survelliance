#!/usr/bin/env python3
import re

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\hdrelay_main.html', encoding='utf-8') as f:
    h = f.read()

m = re.search(r'<title>(.*?)</title>', h)
if m:
    print(f"Title: {m.group(1)}")

# Find all links
print("\nLinks with cam/video/live/gallery/golf/coronado:")
for m in re.finditer(r'href="([^"]+)"', h):
    href = m.group(1)
    if any(k in href.lower() for k in ['cam', 'live', 'gallery', 'video', 'coronado', 'golf', 'demo', 'sample', 'tour', 'preview']):
        print(f"  {href}")

# Look for iframe/embed/video
print("\nIframes/embeds:")
for m in re.finditer(r'<iframe[^>]+src="([^"]+)"', h):
    print(f"  IFRAME: {m.group(1)}")
for m in re.finditer(r'<embed[^>]+src="([^"]+)"', h):
    print(f"  EMBED: {m.group(1)}")

# Look for camera IDs in the page
cids = set(re.findall(r'CID_[A-Z0-9]+', h))
print(f"\nCamera IDs (CID_*) found: {cids}")

# Look for any URLs containing 'cams' or 'stream' or 'live'
print("\nStream/live URLs:")
for m in re.finditer(r'(?:src|href|data)="([^"]*(?:stream|live|cam|video|player)[^"]*)"', h):
    print(f"  {m.group(1)}")

# Print first 2000 chars of content
text = re.sub(r'<script[^>]*>.*?</script>', '', h, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
print(f"\nText (first 2000):\n{text[:2000]}")