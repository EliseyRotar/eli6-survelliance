import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/assets/api-CmVqwtkf.js', headers={'User-Agent':'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
js = r.read().decode('utf-8', errors='replace')
# Look for first occurrence of file: pattern
m = re.search(r'file:"([^"]+)"', js)
if m:
    print('Match:', m.group(0))
# All files
files = re.findall(r'file:"([^"]+)"', js)
print('total files:', len(files))
print('first 20:')
for f in files[:20]:
    print(' ', f)
