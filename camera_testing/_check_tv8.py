import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/assets/api-CmVqwtkf.js', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
js = r.read().decode('utf-8', errors='replace')
print('api length:', len(js))
# Look for Firestore collection names
for m in re.finditer(r'(?:collection|doc|document)\("([^"]+)"', js):
    print(' coll:', m.group(1))
# Look for project IDs
for m in re.finditer(r'projects/([^/"\']+)', js):
    print(' project:', m.group(1))
# Look for Firebase config
for m in re.finditer(r'firebase[A-Z][a-zA-Z]*\s*[=:]\s*\{[^}]+\}', js):
    print(' firebase config:', m.group(0)[:500])
# Look for paths used
for m in re.finditer(r'/v1/[^"\'\\]+', js):
    print(' path:', m.group(0)[:200])
