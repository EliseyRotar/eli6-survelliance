"""HLS proxy server for fl511 (and other CORS-blocked) cam streams.

Smart features:
- CORS headers for browser access
- Auto token refresh: if divas.cloud returns 401, fetch new fl511 session + token and retry
- Live reload of LIVE_URLS JSON
- UI with hls.js player
- /info/<cam_id> endpoint returns URL + token status
"""
import json
import os
import re
import sys
import time
import threading
import urllib.request
import urllib.error
import http.cookiejar
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Add parent dir to import fl511_helpers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl511_helpers as flh

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# Token cache (in-memory + JSON-backed)
# ---------------------------------------------------------------------------
TOKENS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_divas_full_tokens.json'
LIVE_URLS_PATH = TOKENS_PATH  # same file for now

# chan_n -> fl511 image_id (for /stream_url cam_id extraction)
CHAN_TO_CAMID = {}
CHAN_TO_CAMID_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_chan_to_camid.json'
try:
    if os.path.exists(CHAN_TO_CAMID_PATH):
        with open(CHAN_TO_CAMID_PATH, encoding='utf-8') as _f:
            CHAN_TO_CAMID = {int(k): int(v) for k, v in json.load(_f).items()}
        print(f'[HLS Proxy] Loaded {len(CHAN_TO_CAMID)} chan->camid mappings', flush=True)
except Exception as _e:
    print(f'[HLS Proxy] chan map load err: {_e}', flush=True)

# fl511_xflow_cache: cam_id (str) -> {xflow_url, video_url_base, ...}
# Used to pre-warm live URLs without hitting fl511/divas.
XFLOW_CACHE = {}
XFLOW_CACHE_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_xflow_cache.json'
XFLOW_CACHE_MTIME = 0
def load_xflow_cache():
    global XFLOW_CACHE, XFLOW_CACHE_MTIME
    if not os.path.exists(XFLOW_CACHE_PATH):
        return
    try:
        mtime = os.path.getmtime(XFLOW_CACHE_PATH)
        if mtime > XFLOW_CACHE_MTIME:
            with open(XFLOW_CACHE_PATH, encoding='utf-8') as _f:
                XFLOW_CACHE = json.load(_f)
            XFLOW_CACHE_MTIME = mtime
            print(f'[HLS Proxy] Loaded {len(XFLOW_CACHE)} xflow cache entries', flush=True)
    except Exception as _e:
        print(f'[HLS Proxy] xflow cache err: {_e}', flush=True)

LIVE_URLS = {}
LIVE_URLS_MTIME = 0
PROGRESS_LOCK = threading.Lock()

# fl511 session pool for token refresh
SESSION_POOL = []
SESSION_LOCK = threading.Lock()


def load_live_urls():
    """Reload LIVE_URLS from JSON if changed."""
    global LIVE_URLS, LIVE_URLS_MTIME
    try:
        if not os.path.exists(LIVE_URLS_PATH):
            return
        mtime = os.path.getmtime(LIVE_URLS_PATH)
        if mtime > LIVE_URLS_MTIME:
            with open(LIVE_URLS_PATH, encoding='utf-8') as f:
                LIVE_URLS = json.load(f)
            LIVE_URLS_MTIME = mtime
            print(f'[HLS Proxy] Loaded {len(LIVE_URLS):,} live URLs', flush=True)
    except Exception as e:
        print(f'[HLS Proxy] load error: {e}', flush=True)


load_live_urls()


# ---------------------------------------------------------------------------
# fl511 session/token functions
# ---------------------------------------------------------------------------
def _http_get(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36',
    })
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def get_fl_session():
    """Get fresh fl511 session cookies + verification token."""
    try:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj),
            urllib.request.HTTPSHandler(context=ctx),
        )
        req = urllib.request.Request('https://fl511.com/cctv', headers={
            'User-Agent': 'Mozilla/5.0',
        })
        with opener.open(req, timeout=15) as r:
            html = r.read().decode('utf-8', errors='replace')
        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html)
        if not m:
            return None, None
        token = m.group(1)
        cookie_str = '; '.join(f'{c.name}={c.value}' for c in cj)
        return cookie_str, token
    except Exception as e:
        print(f'[HLS Proxy] get_fl_session err: {e}', flush=True)
        return None, None


def get_session():
    """Return a session from the pool, creating one if needed."""
    with SESSION_LOCK:
        # Drop expired sessions (errors >= 5)
        for s in SESSION_POOL:
            if s['errors'] >= 5:
                SESSION_POOL.remove(s)
        if SESSION_POOL:
            return SESSION_POOL[0]
        # Create new
        c, t = get_fl_session()
        if c and t:
            s = {'cookies': c, 'token': t, 'errors': 0, 'created': time.time()}
            SESSION_POOL.append(s)
            return s
        return None


def refresh_session(s):
    """Refresh an expired session."""
    c, t = get_fl_session()
    if c and t:
        s['cookies'] = c
        s['token'] = t
        s['errors'] = 0
        s['created'] = time.time()
        return True
    return False


def get_divas_token_for_cam(cam_id):
    """Fetch a fresh divas token for a specific cam_id.

    cam_id is the fl511 internal cam id (e.g. '617').
    Returns (live_url, token, ts) or (None, None, None).
    """
    s = get_session()
    if not s:
        return None, None, None
    # Determine prefer_host from cache (preserve discovered host) or fallback to CSV lookup
    cached = LIVE_URLS.get(str(cam_id)) or {}
    cached_url = cached.get('live_url', '')
    host_m = re.search(r'(https?://dis-se\d+\.divas\.cloud:8200)', cached_url)
    prefer_host = host_m.group(1) if host_m else flh.build_host_for_chan(int(cam_id) if str(cam_id).isdigit() else 0)
    try:
        url, divas_token, source_id, sys_source = flh.get_divas_token_for_cam(cam_id, s, prefer_host=prefer_host)
        if not url:
            s['errors'] += 1
            return None, None, None
        full_url = url
        # Save to cache (preserves existing keys like 'location')
        with PROGRESS_LOCK:
            existing = LIVE_URLS.get(str(cam_id), {})
            entry = {
                'live_url': full_url,
                'divas_token': divas_token,
                'sourceId': source_id,
                'systemSourceId': sys_source,
                'timestamp': time.time(),
            }
            if 'location' in existing:
                entry['location'] = existing['location']
            LIVE_URLS[str(cam_id)] = entry
        return full_url, divas_token, time.time()
    except Exception as e:
        s['errors'] += 1
        print(f'[HLS Proxy] get_divas_token_for_cam err for {cam_id}: {e}', flush=True)
        return None, None, None


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
class HLSProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_GET(self):
        load_live_urls()
        load_xflow_cache()  # refresh in case daemon wrote new cache
        load_xflow_cache()
        path = self.path.split('?')[0]

        if path == '/' or path == '/index.html':
            self.serve_ui()
            return
        if path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'count': len(LIVE_URLS),
                'sessions': len(SESSION_POOL),
            }).encode())
            return
        if path == '/list':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            items = []
            for cam_id, info in LIVE_URLS.items():
                if not info.get('divas_token'):
                    continue
                items.append({
                    'cam_id': cam_id,
                    'location': info.get('location', ''),
                })
            self.wfile.write(json.dumps(items).encode())
            return
        if path.startswith('/info/'):
            cam_id = path[6:]
            info = LIVE_URLS.get(cam_id, {})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            ts = info.get('timestamp', 0)
            age = round(time.time() - ts, 1) if ts else None
            self.wfile.write(json.dumps({
                'cam_id': cam_id,
                'has_url': bool(info.get('live_url')),
                'token_age_sec': age,
            }).encode())
            return
        if path.startswith('/refresh/'):
            # Force-refresh a cam's token
            cam_id = path[9:]
            url, token, ts = get_divas_token_for_cam(cam_id)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            if url:
                # Persist
                _persist_tokens()
                self.wfile.write(json.dumps({'ok': True, 'url': url[:100] + '...'}).encode())
            else:
                self.wfile.write(json.dumps({'ok': False, 'error': 'token refresh failed'}).encode())
            return
        if path.startswith('/snapshot/'):
            cam_id = path[10:]
            url = LIVE_URLS.get(cam_id, {}).get('live_url', '')
            self.proxy_snapshot(url)
            return
        if path.startswith('/stream_url'):
            # Generic HLS proxy: ?u=<full m3u8 url>&cam_id=<optional cam_id>
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            url = (qs.get('u') or [''])[0]
            cam_id = (qs.get('cam_id') or [None])[0]
            if not url:
                self.send_error(400, 'missing u parameter')
                return
            # If cam_id not provided, extract from URL chan-N
            if not cam_id and 'chan-' in url:
                m = re.search(r'chan-(\d+)_h', url)
                if m:
                    chan_n = int(m.group(1))
                    cam_id = str(CHAN_TO_CAMID.get(chan_n, '')) or None
            self.proxy_hls(cam_id, url)
            return
        if path.startswith('/stream/'):
            cam_id = path[8:]
            url = LIVE_URLS.get(cam_id, {}).get('live_url', '')
            if not url:
                # No cached URL — try to fetch fresh
                url, _, _ = get_divas_token_for_cam(cam_id)
                if url:
                    _persist_tokens()
            if url:
                self.proxy_hls(cam_id, url)
                return
            self.send_error(404, 'Stream not found and no fl511 data for cam_id=' + cam_id)
            return
        self.send_error(404)

    def proxy_hls(self, cam_id, url):
        """Proxy HLS stream. Auto-refresh token on 401.

        fl511 specific: If URL points to index.m3u8, rewrite to xflow.m3u8
        (the live media playlist) before fetching. This is the workaround
        from pitchbytez99/florida_traffic_cameras analysis.
        """
        def fix_xflow(u):
            """fl511: replace index.m3u8 with xflow.m3u8 to get the live media playlist"""
            if 'divas.cloud' in u and 'index.m3u8' in u:
                return u.replace('index.m3u8', 'xflow.m3u8')
            return u

        # Fast path: if cam_id is known and we have a cached xflow URL, use it
        # (the cache has a recent fresh token, so it'll likely work)
        if cam_id and str(cam_id) in XFLOW_CACHE:
            entry = XFLOW_CACHE[str(cam_id)]
            cached_xflow = entry.get('xflow_url', '')
            if cached_xflow:
                # Replace host part of cached URL with host from current URL (handles chan_id reuse across servers)
                # In practice the host is determined by cam_id, so just use cached as-is
                url = cached_xflow

        url = fix_xflow(url)
        # Try the URL. If 401/403/429, refresh token and retry once.
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Origin': 'https://fl511.com',
                    'Referer': 'https://fl511.com/',
                })
                r = urllib.request.urlopen(req, timeout=15, context=ctx)
                try:
                    # Reset wfile position just in case
                    print(f'[HLS Proxy] Got r.status={r.status}, ct={r.headers.get("Content-Type")}, len={r.headers.get("Content-Length")}', flush=True)
                    if r.status == 200:
                        data = r.read()
                        # Rewrite m3u8 relative URLs
                        if b'.m3u8' in url.encode() and (b'#EXTM3U' in data or b'#EXT-X' in data):
                            text = data.decode('utf-8', errors='replace')
                            base_url = '/'.join(url.split('/')[:4])
                            # First handle #EXT-X-MAP:URI="..." style (any URL inside quotes)
                            text = re.sub(r'URI="([^"]+)"', f'URI="{base_url}/\\1"', text)
                            # Then handle direct seg refs (lines not starting with #)
                            text = re.sub(r'(?m)^([^#\n].*?\.m3u8.*?)$', f'{base_url}/\\1', text)
                            text = re.sub(r'(?m)^([^#\n].*?_init\.mp4.*?)$', f'{base_url}/\\1', text)
                            text = re.sub(r'(?m)^([^#\n].*?_seg\d+\.mp4.*?)$', f'{base_url}/\\1', text)
                            text = re.sub(r'(?m)^([^#\n].*?_seg\d+\.ts.*?)$', f'{base_url}/\\1', text)
                            data = text.encode('utf-8')
                        # Now send headers with correct Content-Length
                        self.send_response(r.status)
                        for h in ('Content-Type', 'Cache-Control'):
                            if h in r.headers:
                                self.send_header(h, r.headers[h])
                        self.send_header('Content-Length', str(len(data)))
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', '*')
                        self.end_headers()
                        self.wfile.write(data)
                        return
                    else:
                        # Non-200, just forward as-is
                        data = r.read()
                        self.send_response(r.status)
                        for h in ('Content-Type', 'Content-Length', 'Cache-Control'):
                            if h in r.headers:
                                self.send_header(h, r.headers[h])
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', '*')
                        self.end_headers()
                        self.wfile.write(data)
                        return
                finally:
                    r.close()
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404, 429) and attempt == 0:
                    # Token expired or chan doesn't exist anymore — refresh
                    print(f'[HLS Proxy] {e.code} on {cam_id}, refreshing token', flush=True)
                    new_url, _, _ = get_divas_token_for_cam(cam_id)
                    if new_url:
                        _persist_tokens()
                        url = fix_xflow(new_url)
                        continue
                    else:
                        # Refresh failed — return 502
                        self.send_error(502, 'Token refresh failed')
                        return
                else:
                    self.send_error(e.code, str(e))
                    return
            except Exception as e:
                if attempt == 0:
                    # Try refresh once
                    new_url, _, _ = get_divas_token_for_cam(cam_id)
                    if new_url:
                        _persist_tokens()
                        url = fix_xflow(new_url)
                        continue
                self.send_error(502, str(e))
                return
        # Exhausted retries
        self.send_error(502, 'Token refresh exhausted retries')

    def proxy_snapshot(self, url):
        """Try to get a snapshot from HLS stream."""
        try:
            self.send_response(302)
            img_url = url.replace('/chan-', '/map/Cctv/').replace('/index.m3u8', '')
            self.send_header('Location', f'https://fl511.com/map/Cctv/{url.split("/")[-2].split("_")[0]}')
            self.end_headers()
        except Exception:
            self.send_error(404)

    def serve_ui(self):
        html = '''<!DOCTYPE html>
<html>
<head>
<title>HLS Proxy - FL511 Live Cams</title>
<style>
  body { font-family: monospace; background: #111; color: #ddd; padding: 10px; margin: 0; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 8px; }
  .cam { background: #222; padding: 6px; border-radius: 4px; }
  .cam h3 { margin: 0 0 4px 0; font-size: 12px; }
  .cam video { width: 100%; height: 240px; background: #000; }
  .stats { padding: 6px; background: #222; border-radius: 4px; margin-bottom: 8px; }
</style>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.13"></script>
</head>
<body>
<h2>FL511 Live HLS Streams (auto token refresh)</h2>
<div class="stats" id="stats">Loading...</div>
<input type="text" id="search" placeholder="Search cams..." style="width:100%;padding:8px;background:#222;color:#fff;border:1px solid #444" />
<div class="grid" id="grid"></div>
<script>
let cams = [];
let hls = {};
async function load() {
  const r = await fetch('/list');
  cams = await r.json();
  document.getElementById('stats').innerHTML = 'Total: ' + cams.length;
  render();
}
function render() {
  const q = document.getElementById('search').value.toLowerCase();
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  for (let i = 0; i < cams.length; i++) {
    const c = cams[i];
    if (q && !(c.cam_id.includes(q) || (c.location||'').toLowerCase().includes(q))) continue;
    const div = document.createElement('div');
    div.className = 'cam';
    div.innerHTML = '<h3>' + (c.location || 'cam ' + c.cam_id) + '</h3><video data-cam="' + c.cam_id + '" muted playsinline autoplay controls></video>';
    grid.appendChild(div);
    const v = div.querySelector('video');
    if (Hls.isSupported()) {
      hls[c.cam_id] = new Hls();
      hls[c.cam_id].loadSource('/stream/' + c.cam_id);
      hls[c.cam_id].attachMedia(v);
    } else if (v.canPlayType('application/vnd.apple.mpegurl')) {
      v.src = '/stream/' + c.cam_id;
    }
  }
}
document.getElementById('search').addEventListener('input', render);
load();
</script>
</body>
</html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html.encode())


def _persist_tokens():
    """Save the LIVE_URLS dict back to disk atomically."""
    try:
        with PROGRESS_LOCK:
            tmp = LIVE_URLS_PATH + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(LIVE_URLS, f, indent=2)
            os.replace(tmp, LIVE_URLS_PATH)
    except Exception as e:
        print(f'[HLS Proxy] persist err: {e}', flush=True)


def main():
    sys.stdout.reconfigure(line_buffering=True)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    print(f'[HLS Proxy] Starting on port {port} with auto token refresh...', flush=True)
    server = ThreadingHTTPServer(('0.0.0.0', port), HLSProxyHandler)
    print(f'[HLS Proxy] Listening on http://0.0.0.0:{port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
