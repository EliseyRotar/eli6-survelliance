"""Extract all source IDs from trafficvision.live api.js and probe each one."""
import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/assets/api-CmVqwtkf.js', headers={'User-Agent':'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
js = r.read().decode('utf-8', errors='replace')
files = re.findall(r'file:"([^"]+)"', js)
print('total files:', len(files))
sources = []
for f in files:
    # Strip '-cameras.json' suffix
    source_id = f.replace('-cameras.json', '')
    sources.append(source_id)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_sources.txt', 'w') as f:
    for s in sorted(set(sources)):
        f.write(s + '\n')
print(f'saved {len(set(sources))} unique sources to trafficvision_sources.txt')
