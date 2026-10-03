import urllib.request, socket, re
socket.setdefaulttimeout(15)
# Get the firebase-vendor JS
req = urllib.request.Request('https://trafficvision.live/assets/firebase-vendor-zv39oyyy.js', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
js = r.read().decode('utf-8', errors='replace')
print('firebase-vendor length:', len(js))
# Find all string literals that look like project IDs
matches = re.findall(r'"([a-z][a-z0-9-]{4,30})"', js)
projects = [m for m in matches if 'project' in m.lower() or 'firebase' in m.lower() or 'trafficvision' in m.lower() or 'tv-' in m.lower()]
print('project-like strings:', set(projects[:30]))
# Also dump any key=value patterns with quotes
for m in re.finditer(r'(?:projectId|apiKey|databaseURL|storageBucket|authDomain|appId)["\s:]+["\']([^"\']+)', js):
    print('  KEY:', m.group(0)[:120])
