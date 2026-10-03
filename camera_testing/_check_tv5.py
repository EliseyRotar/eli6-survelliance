import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
html = r.read().decode('utf-8', errors='replace')
# Look for src and href
for m in re.finditer(r'(?:src|href)=["\']([^"\']+)', html):
    u = m.group(1)
    if 'firebase' in u.lower() or 'firestore' in u.lower() or 'api' in u.lower():
        print('FB API:', u)
# Look for inline scripts with firebase
for m in re.finditer(r'<script[^>]*>([^<]+)</script>', html):
    s = m.group(1)
    if 'firebase' in s.lower() or 'firestore' in s.lower() or 'project' in s.lower():
        print('INLINE SCRIPT:', s[:800])
        print('---')
