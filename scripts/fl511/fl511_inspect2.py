"""Find fl511 AJAX endpoint by inspecting the page HTML."""
import urllib.request
import re

url = 'https://fl511.com/cctv'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=30) as r:
    html = r.read().decode('utf-8', errors='replace')

# Save HTML for inspection
with open('fl511_cctv_page.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'HTML size: {len(html):,} bytes')

# Find AJAX endpoints
print('\n=== AJAX / API endpoints ===')
seen = set()
for m in re.finditer(r'(?:url|src|href|action)\s*[:=]\s*["\']([^"\']*(?:/api/|/CCTV/|/Cctv/|GetCams|getcam|GetCam|/video|/stream|ListData|DataTable|/data/|cctv-?data)[^"\']*)', html, re.I):
    u = m.group(1)
    if u not in seen:
        seen.add(u)
        print(f'  {u[:200]}')

# Find the table init script
print('\n=== DataTables init ===')
for m in re.finditer(r'(?:ajax|source)\s*[:=]\s*([^,;\n]+)', html, re.I):
    txt = m.group(1).strip()[:300]
    if any(k in txt.lower() for k in ['url', 'data', 'ajax', 'get', 'json', 'api', 'cctv', 'cam']):
        print(f'  {txt}')

# Find any JS variable assignments
print('\n=== JS variables with cams ===')
for m in re.finditer(r'(?:var|let|const)\s+(\w+)\s*=\s*["\']([^"\']+)["\']', html):
    name = m.group(1)
    val = m.group(2)
    if any(k in val.lower() for k in ['cam', 'cctv', 'api', 'stream', 'data']):
        print(f'  {name} = {val[:200]}')

# Find Show Video / Hide Video button click handler
print('\n=== Show Video handlers ===')
for m in re.finditer(r'(Show\s*Video|getCamVideo|videoUrl|VideoUrl|streamUrl|videoSrc|videoSrc|video_url|video_url|camVideoUrl)', html, re.I):
    start = max(0, m.start() - 50)
    end = min(len(html), m.end() + 100)
    snippet = html[start:end].replace('\n', ' ').replace('\r', ' ')
    print(f'  {snippet[:250]}')
    break

# Find map of camID -> video stream
print('\n=== Look for cam->video mapping ===')
# Look for /api/Cctv/...
for m in re.finditer(r'["\'](/api/Cctv/[^"\']*)["\']', html, re.I):
    print(f'  {m.group(1)[:200]}')
# Look for /api/CCTV/...
for m in re.finditer(r'["\'](/api/CCTV/[^"\']*)["\']', html, re.I):
    print(f'  {m.group(1)[:200]}')
# Look for videoUrl template
for m in re.finditer(r'["\']([^"\']*video[^"\']*\.mp4[^"\']*)["\']', html, re.I):
    print(f'  mp4: {m.group(1)[:200]}')
for m in re.finditer(r'["\']([^"\']*\.m3u8[^"\']*)["\']', html, re.I):
    print(f'  m3u8: {m.group(1)[:200]}')
