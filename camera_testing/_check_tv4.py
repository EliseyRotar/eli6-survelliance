import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
html = r.read().decode('utf-8', errors='replace')
# Search for Firebase config
fb_configs = re.findall(r'firebaseConfig[^}]*\}', html)
print('firebase configs:')
for c in fb_configs[:3]:
    print(c[:500])
print()
# Find project IDs (with single quotes)
pid = re.findall(r"projectId['\"\s:=]+([a-zA-Z0-9-]+)", html)
print('project IDs:', pid[:10])
# Find API keys
keys = re.findall(r"apiKey['\"\s:=]+['\"]([^'\"]+)", html)
print('api keys:', keys[:3])
# Find any fetch URLs
fetch_urls = re.findall(r'fetch\([\"\'](https?://[^\"\']+)', html)
print('fetch URLs:')
for u in fetch_urls[:10]:
    print(' ', u)
