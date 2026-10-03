"""
SkylineWebcams HLS Token Refresher (long-running daemon).

Fetches fresh HLS tokens every 4 minutes (tokens expire in ~5 min).
Saves tokens to JSON file for the HLS proxy to use.
"""
import urllib.request, re, json, sys, os, time
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# All known cam URLs (SkylineWebcams cams with HLS only)
CAM_URLS = {
    998: 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/le-castella.html',
    104: 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/isola-capo-rizzuto-le-castella.html',
    5612: 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/carfizzi.html',
    203: 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/villaggio-palumbo.html',
    1627: 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/palumbo-sila-lago-ampollino.html',
    1398: 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/palumbo-sila.html',
    1363: 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/lago-ampollino-cotronei.html',
    1478: 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/torre-melissa.html',
    1479: 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/torre-melissa-calabria.html',
    580: 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/porto-crotone.html',
}

# Load all URLs from url_map.json
try:
    with open(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\skyline_url_map.json') as f:
        url_map = json.load(f)
    for cid_str, url in url_map.items():
        CAM_URLS[int(cid_str)] = url
except: pass

print(f'SkylineWebcams cams to refresh: {len(CAM_URLS)}')


def fetch_token(page_url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(page_url, headers={
                'User-Agent': UA,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'identity',
            })
            r = urllib.request.urlopen(req, timeout=30)
            body = r.read().decode('utf-8', errors='replace')
            m = re.search(r"source:\s*['\"]([^'\"]*livee\.m3u8[^'\"]*)['\"]", body)
            if m:
                return m.group(1)
            m2 = re.search(r"livee\.m3u8\?a=([a-z0-9]+)", body)
            if m2:
                return f"livee.m3u8?a={m2.group(1)}"
        except urllib.request.HTTPError as e:
            if e.code == 503:
                time.sleep(5)
                continue
        except:
            pass
        time.sleep(2)
    return None


def verify_hls(token_path):
    try:
        url = f'https://hd-auth.skylinewebcams.com/{token_path}'
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': 'https://www.skylinewebcams.com/'})
        r = urllib.request.urlopen(req, timeout=10)
        body = r.read().decode('utf-8', errors='replace')
        ct = r.headers.get('Content-Type','')
        is_live = '#EXT-X-ENDLIST' not in body
        return is_live, ct
    except:
        return False, None


def refresh_all():
    print(f'=== Refresh cycle {time.strftime("%H:%M:%S")} ===')
    tokens = {}
    stats = {'live': 0, 'expired': 0, 'no_token': 0}
    start = time.time()
    for i, (cam_id, page_url) in enumerate(CAM_URLS.items()):
        token_path = fetch_token(page_url)
        if token_path:
            is_live, ct = verify_hls(token_path)
            full_url = f'https://hd-auth.skylinewebcams.com/{token_path}'
            tokens[cam_id] = {
                'page_url': page_url,
                'token_path': token_path,
                'hls_url': full_url,
                'live': is_live,
                'fetched_at': time.time(),
                'content_type': ct,
            }
            if is_live:
                stats['live'] += 1
            else:
                stats['expired'] += 1
        else:
            tokens[cam_id] = {'page_url': page_url, 'error': 'no_token', 'fetched_at': time.time()}
            stats['no_token'] += 1
        if i % 10 == 0:
            print(f'  {i}/{len(CAM_URLS)} ({time.time()-start:.0f}s) stats={stats}')
        time.sleep(0.4)

    # Save
    with open(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\skyline_hls_tokens.json', 'w', encoding='utf-8') as f:
        json.dump({str(k): v for k, v in tokens.items()}, f, indent=2)

    elapsed = time.time() - start
    print(f'Done in {elapsed:.0f}s. LIVE: {stats["live"]}, Expired: {stats["expired"]}, No token: {stats["no_token"]}')


if __name__ == '__main__':
    while True:
        try:
            refresh_all()
        except Exception as e:
            print(f'ERROR: {repr(e)}')
        # Wait 4 minutes before next refresh (tokens expire ~5 min)
        time.sleep(240)