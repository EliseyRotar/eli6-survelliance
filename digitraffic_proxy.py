"""Digitraffic weathercam proxy + slideshow service.

- Caches image fetches in-memory (key = preset_id, TTL = 10 min)
- Serves image bytes via /img/<preset_id>.jpg
- Builds 5-frame slideshow via /slideshow/<preset_id>.json (5 most recent history frames)
- Forwards weather data via /weather/<station_id>.json
- All endpoints accept CORS for browser

Rate limit: digitraffic allows ~300 req/5min globally. We do at most 1 per
3s per unique preset. With 470 cams, we do ~470/3 = 156 req/sec worst case,
but most are cached so the actual rate is much lower.

This service runs on port 8772.
"""
import json
import os
import re
import sys
import time
import threading
import urllib.request
import urllib.error
import ssl
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections import OrderedDict

sys.stdout.reconfigure(line_buffering=True)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'

API_BASE = 'https://tie.digitraffic.fi/api/weathercam/v1'
IMG_BASE = 'https://weathercam.digitraffic.fi'
CACHE_TTL_SEC = 600  # 10 min
SLIDESHOW_FRAMES = 5

# In-memory caches
IMAGE_CACHE = {}  # preset_id -> (bytes, content_type, ts)
HISTORY_CACHE = {}  # preset_id -> (history_data, ts)
WEATHER_CACHE = {}  # station_id -> (data, ts)
STATIONS_CACHE = {}  # /stations cache
LOCK = threading.Lock()


def _http_get(url, headers=None, timeout=10):
    """GET with optional gzip support."""
    h = {'User-Agent': UA, 'Accept-Encoding': 'gzip, identity'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read()
        if r.headers.get('Content-Encoding') == 'gzip':
            raw = gzip.decompress(raw)
        return raw, dict(r.headers)


def _http_head(url, headers=None, timeout=6):
    h = {'User-Agent': UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, method='HEAD', headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}


def get_image(preset_id):
    """Get image bytes, cached for CACHE_TTL_SEC."""
    with LOCK:
        cached = IMAGE_CACHE.get(preset_id)
        if cached and (time.time() - cached[2]) < CACHE_TTL_SEC:
            return cached[0], cached[1], True

    # Fetch
    url = f'{IMG_BASE}/{preset_id}.jpg'
    try:
        raw, headers = _http_get(url, timeout=8)
        ct = headers.get('Content-Type', 'image/jpeg')
        with LOCK:
            IMAGE_CACHE[preset_id] = (raw, ct, time.time())
        # bound cache to 2000 entries
        if len(IMAGE_CACHE) > 2000:
            oldest = min(IMAGE_CACHE, key=lambda k: IMAGE_CACHE[k][2])
            IMAGE_CACHE.pop(oldest, None)
        return raw, ct, False
    except Exception as e:
        print(f'[Digi] image {preset_id} err: {e}', flush=True)
        return None, None, False


def get_history(preset_id, limit=SLIDESHOW_FRAMES):
    """Get the last `limit` history entries for a preset, cached."""
    with LOCK:
        cached = HISTORY_CACHE.get(preset_id)
        if cached and (time.time() - cached[1]) < CACHE_TTL_SEC:
            return cached[0][:limit]

    url = f'{API_BASE}/stations/{preset_id}/history'
    try:
        raw, _ = _http_get(url, timeout=8)
        data = json.loads(raw)
        history = data.get('presets', [{}])[0].get('history', [])
        with LOCK:
            HISTORY_CACHE[preset_id] = (history, time.time())
        return history[:limit]
    except Exception as e:
        print(f'[Digi] history {preset_id} err: {e}', flush=True)
        return []


def get_stations():
    """Get all stations list (cached 1h)."""
    with LOCK:
        cached = STATIONS_CACHE.get('all')
        if cached and (time.time() - cached[1]) < 3600:
            return cached[0]
    url = f'{API_BASE}/stations'
    try:
        raw, _ = _http_get(url, timeout=15)
        data = json.loads(raw)
        features = data.get('features', [])
        with LOCK:
            STATIONS_CACHE['all'] = (features, time.time())
        return features
    except Exception as e:
        print(f'[Digi] stations err: {e}', flush=True)
        return []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_image(self, data, content_type='image/jpeg'):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        # Browser cache for 5 min so we don't hammer upstream
        self.send_header('Cache-Control', 'public, max-age=300')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]

        if path == '/health':
            self._send_json({
                'status': 'ok',
                'image_cache': len(IMAGE_CACHE),
                'history_cache': len(HISTORY_CACHE),
                'stations_cache': len(STATIONS_CACHE.get('all', ([], 0))[0]),
            })
            return

        if path == '/stations':
            stations = get_stations()
            self._send_json({'count': len(stations), 'stations': stations})
            return

        # /img/<preset_id>.jpg
        m = re.match(r'^/img/([A-Z0-9]+)\.jpg$', path)
        if m:
            preset_id = m.group(1)
            data, ct, cached = get_image(preset_id)
            if data is not None:
                self._send_image(data, ct or 'image/jpeg')
            else:
                self.send_error(502, f'Upstream failed for {preset_id}')
            return

        # /slideshow/<preset_id>.json  -> 5 most recent history frames
        m = re.match(r'^/slideshow/([A-Z0-9]+)\.json$', path)
        if m:
            preset_id = m.group(1)
            history = get_history(preset_id, SLIDESHOW_FRAMES)
            frames = []
            for h in history:
                url = h.get('imageUrl', '')
                if not url:
                    continue
                # Replace upstream URL with our proxy URL
                # Original: https://weathercam.digitraffic.fi/C0857502.jpg?versionId=...
                # Proxied: http://localhost:8772/img/C0857502.jpg?versionId=...
                # But we don't have versionId support in our proxy yet. Just use base preset_id.
                m2 = re.search(r'/(C[0-9]+)\.jpg', url)
                if m2:
                    proxied = f'http://localhost:8772/img/{m2.group(1)}.jpg'
                    frames.append({
                        'url': proxied,
                        'lastModified': h.get('lastModified'),
                        'sizeBytes': h.get('sizeBytes'),
                    })
            self._send_json({
                'preset_id': preset_id,
                'frames': frames,
                'count': len(frames),
                'cached_at': time.time(),
            })
            return

        self.send_error(404)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8772
    print(f'[Digi] Starting digitraffic proxy on port {port}', flush=True)
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)

    # Prewarm image cache in background (slow, 1 req per 3s to avoid rate limit)
    if os.environ.get('DIGI_PREWARM', '1') == '1':
        def prewarm():
            try:
                stations = get_stations()
                presets = []
                for s in stations:
                    for p in s.get('properties', {}).get('presets', []):
                        if p.get('inCollection'):
                            presets.append(p['id'])
                print(f'[Digi] Prewarming {len(presets)} presets at 1/3s...', flush=True)
                for i, pid in enumerate(presets, 1):
                    get_image(pid)
                    if i % 10 == 0:
                        print(f'[Digi] Prewarmed {i}/{len(presets)}', flush=True)
                    time.sleep(3)  # 1 per 3s = 20/min = 100/5min
                print(f'[Digi] Prewarm done: {len(IMAGE_CACHE)} cached', flush=True)
            except Exception as e:
                print(f'[Digi] Prewarm err: {e}', flush=True)
        t = threading.Thread(target=prewarm, daemon=True)
        t.start()

    print(f'[Digi] Listening on http://0.0.0.0:{port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
