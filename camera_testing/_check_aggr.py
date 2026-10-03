import urllib.request, socket, re
socket.setdefaulttimeout(10)
urls = [
    'https://www.webcamtaxi.com/en/webcams.html',
    'https://www.skylinewebcams.com/en/webcams.html',
    'https://www.seewebcams.com/',
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 Chrome/124.0'})
        r = urllib.request.urlopen(req, timeout=6)
        html = r.read().decode('utf-8', errors='replace')
        urls_in = re.findall(r'(?:src|href)\s*=\s*"\'(https?://[^"\']+\.(?:jpg|png|mjpg|m3u8|mp4)[^"\']*)', html, re.I)
        print(u[:60], '->', r.status, len(html), 'images:', len(urls_in))
        for x in urls_in[:5]:
            print('   ', x[:90])
    except Exception as e:
        print(u[:60], '->', str(e)[:80])
