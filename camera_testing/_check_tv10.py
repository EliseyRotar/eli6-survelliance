import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/assets/api-CmVqwtkf.js', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
js = r.read().decode('utf-8', errors='replace')
print('api length:', len(js))
# Save for offline analysis
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\_api.js', 'w', encoding='utf-8') as f:
    f.write(js)
# Look for collection names
patterns = [
    r'collection\([\"\']([^\"\']+)',
    r'collection\(["\']?([^"\']+?)["\']?,',
    r'firestore\.collection\([\"\']([^\"\']+)',
    r'["\'](?:cameras|feeds|caltrans|txdot|fdot|cdot|nyc|texas|california|florida|newyork)["\']',
    r'projectId["\',\s:]+["\']([a-z0-9-]+)',
]
for pat in patterns:
    matches = list(re.finditer(pat, js))
    if matches:
        print(f'\n=== Pattern: {pat} ===')
        seen = set()
        for m in matches[:30]:
            v = m.group(1) if m.lastindex else m.group(0)
            if v not in seen:
                seen.add(v)
                print(f'  {v[:200]}')
