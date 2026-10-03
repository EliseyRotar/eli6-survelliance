"""Find Windy video URLs through their internal API."""

import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

WINDY_IDS = [1597690315, 1793898215, 1793902097]


def get(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read()
            ct = r.headers.get('Content-Type', '')
            return (r.status, ct, data)
    except urllib.error.HTTPError as e:
        return (e.code, '', b'')
    except Exception as e:
        return (-1, str(e).encode(), b'')


endpoints_to_try = [
    'https://webcams.windy.com/webcams/api/v3/webcams/{id}',
    'https://webcams.windy.com/webcams/api/v2/webcam/{id}',
    'https://webcams.windy.com/webcams/api/webcam/{id}',
    'https://webcams.windy.com/api/webcam/{id}',
    'https://www.windy.com/webcam/{id}.json',
    'https://www.windy.com/api/webcam/{id}',
    'https://www.windy.com/api/webcams/{id}',
    'https://webcams.windy.com/api/m3u8/{id}',
    'https://webcams.windy.com/webcams/{id}/m3u8',
    'https://webcams.windy.com/webcams/{id}.m3u8',
    'https://webcam.windy.com/webcams/{id}/embed',
    'https://www.windy.com/-Webcam/{id}',
    'https://webcams.windy.com/webcam/{id}',
]

for cam_id in WINDY_IDS[:1]:
    print(f'\n=== Testing Windy cam {cam_id} ===')
    for ep in endpoints_to_try:
        url = ep.format(id=cam_id)
        status, ct, data = get(url)
        if status == 200 and len(data) > 50:
            preview = data[:200].decode('utf-8', errors='replace')
            print(f'  [{status} {ct[:30]}] {url}')
            video_refs = re.findall(r'["\'](https?://[^"\']+\.(?:mp4|m3u8|hls|webm)[^"\']*)["\']',
                                    data.decode('utf-8', errors='replace'), re.I)
            if video_refs:
                for v in video_refs[:5]:
                    print(f'    VIDEO: {v[:120]}')


print('\n=== Windy size variants ===')
for cam_id in WINDY_IDS:
    for sz_path in [
        f'/15/{cam_id}/current/0/0/{cam_id}.jpg',
        f'/15/{cam_id}/current/0/{cam_id}.mp4',
        f'/15/{cam_id}/original/{cam_id}.mp4',
        f'/15/{cam_id}/live/{cam_id}.mp4',
        f'/15/{cam_id}/live.mp4',
        f'/97/{cam_id}/live.mp4',
        f'/15/{cam_id}/full/0/{cam_id}.mp4',
    ]:
        url = f'https://images-webcams.windy.com{sz_path}'
        status, ct, data = get(url, timeout=6)
        if status == 200:
            print(f'  [{status} {ct[:30]}] {sz_path}')


# Also test if Windy has HLS via embed player
print('\n=== Windy embed player M3U8 ===')
for cam_id in WINDY_IDS[:1]:
    for path in [
        f'/webcams/public/embed/player/{cam_id}/m3u8',
        f'/public/embed/player/{cam_id}.m3u8',
        f'/api/cam/{cam_id}/m3u8',
        f'/api/v3/webcam/{cam_id}.m3u8',
    ]:
        for prefix in ['https://webcams.windy.com']:
            url = prefix + path
            status, ct, data = get(url)
            if status == 200:
                print(f'  [{status} {ct[:30]}] {url}')


# Test for hlsjs playlist
print('\n=== Try embed iframe M3U8 endpoints ===')
for cam_id in WINDY_IDS:
    url = f'https://webcams.windy.com/public/embed/player/{cam_id}'
    status, ct, data = get(url)
    if status == 200:
        # Look for m3u8 in response
        refs = re.findall(r'([^\s"\'<>]+\.m3u8[^\s"\'<>]*)', data.decode('utf-8', errors='replace'))
        refs += re.findall(r'src[\'"]?\s*[=:]\s*[\'"]([^\'"]+)[\'"]', data.decode('utf-8', errors='replace'))
        if refs:
            for r in refs[:5]:
                print(f'  Cam {cam_id}: {r[:120]}')
