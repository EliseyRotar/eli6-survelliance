import urllib.request, socket, re, json
socket.setdefaulttimeout(15)
url = 'https://trafficvision.live/blog/a-coruna-traffic-cameras'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
html = r.read().decode('utf-8', errors='replace')
print('html size:', len(html))
# Find video/image URLs
patterns = [
    r'videoUrl["\s:=]+["\']([^"\']+)',
    r'imageUrl["\s:=]+["\']([^"\']+)',
    r'youtubeVideoId["\s:=]+["\']([^"\']+)',
    r'playerUrl["\s:=]+["\']([^"\']+)',
    r'feedUrl["\s:=]+["\']([^"\']+)',
    r'hls["\s:=]+["\']([^"\']+)',
    r'playlist\.m3u8',
    r'\.mp4',
]
for pat in patterns:
    matches = re.findall(pat, html)
    if matches:
        print(f'\n{pat[:30]} ({len(matches)} hits):')
        for m in matches[:5]:
            print(' ', m[:200])
# Save HTML
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\_blog_sample.html', 'w', encoding='utf-8') as f:
    f.write(html)
