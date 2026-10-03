import requests, re
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'
s = requests.Session()
s.headers.update({'User-Agent': UA})
r = s.get('https://www.opentopia.com/webcam.php?cid=15', timeout=10)
print('status:', r.status_code, 'len:', len(r.text))
imgs = re.findall(r'<img[^>]+src="([^"]+\.jpg)"', r.text)
print('imgs:', len(imgs))
for i in imgs[:5]: print(i)
# look for ip:port patterns
live = re.findall(r'(https?://[^"\'\s<>]+\.(?:jpg|mjpg|mjpeg))', r.text, re.I)
print('live:', len(live))
for i in live[:5]: print('  L:', i)
# look for /webcam/ urls
wurls = re.findall(r'href="([^"]*webcam[^"]+)"', r.text, re.I)
print('webcam urls:', len(wurls))
for i in wurls[:5]: print('  W:', i)
