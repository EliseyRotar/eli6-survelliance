"""SkylineWebcams HLS proxy - simple standalone.

Serves SkylineWebcams HLS streams at /skyline/<cam_id>/stream.m3u8
Reads fresh tokens from /tmp/skyline_hls_tokens.json (or fetch fresh if needed)
"""
import http.server, json, os, re, sys, time, urllib.request, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TOKENS_PATH = r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\skyline_hls_tokens.json'
PAGE_URLS_PATH = r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\skyline_url_map.json'

TOKENS = {}
PAGE_URLS = {}
TOKENS_MTIME = 0

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'


def load_tokens():
    global TOKENS, TOKENS_MTIME, PAGE_URLS
    if os.path.exists(TOKENS_PATH):
        mtime = os.path.getmtime(TOKENS_PATH)
        if mtime > TOKENS_MTIME:
            try:
                with open(TOKENS_PATH) as f:
                    TOKENS = json.load(f)
                TOKENS_MTIME = mtime
            except: pass
    if os.path.exists(PAGE_URLS_PATH):
        with open(PAGE_URLS_PATH) as f:
            PAGE_URLS = json.load(f)
    # add 11 known ICR cams
    PAGE_URLS.update({
        '998': 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/le-castella.html',
        '104': 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/isola-capo-rizzuto-le-castella.html',
        '5612': 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/carfizzi.html',
        '203': 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/villaggio-palumbo.html',
        '1627': 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/palumbo-sila-lago-ampollino.html',
        '1398': 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/palumbo-sila.html',
        '1363': 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/lago-ampollino-cotronei.html',
        '1478': 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/torre-melissa.html',
        '1479': 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/torre-melissa-calabria.html',
        '580': 'https://www.skylinewebcams.com/en/webcam/italia/calabria/crotone/porto-crotone.html',
    })


def fetch_token(page_url, retries=2):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(page_url, headers={
                'User-Agent': UA,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'identity',
            })
            r = urllib.request.urlopen(req, timeout=15)
            body = r.read().decode('utf-8', errors='replace')
            m = re.search(r"source:\s*['\"]([^'\"]*livee\.m3u8[^'\"]*)['\"]", body)
            if m:
                return m.group(1)
        except: pass
        time.sleep(1)
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write(f'[SKYLINE] {fmt}\n')

    def do_GET(self):
        load_tokens()
        if self.path == '/' or self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            live = sum(1 for v in TOKENS.values() if v.get('live'))
            body = json.dumps({'status': 'ok', 'count': len(TOKENS), 'live': live, 'version': '1.0'}).encode()
            self.wfile.write(body)
            return

        if self.path.startswith('/skyline/'):
            # /skyline/<cam_id>/stream.m3u8
            parts = self.path.split('/')
            if len(parts) >= 3:
                cam_id = parts[2]
                if cam_id in PAGE_URLS:
                    # get fresh token if expired
                    info = TOKENS.get(cam_id, {})
                    hls_url = info.get('hls_url')
                    fetched_at = info.get('fetched_at', 0)
                    age = time.time() - fetched_at
                    if not hls_url or age > 240 or not info.get('live'):
                        # refresh
                        token_path = fetch_token(PAGE_URLS[cam_id])
                        if token_path:
                            hls_url = f'https://hd-auth.skylinewebcams.com/{token_path}'
                        else:
                            self.send_response(404)
                            self.end_headers()
                            return
                    # proxy the manifest
                    try:
                        req = urllib.request.Request(hls_url, headers={
                            'User-Agent': UA,
                            'Referer': 'https://www.skylinewebcams.com/',
                        })
                        r = urllib.request.urlopen(req, timeout=10)
                        body = r.read()
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                        self.end_headers()
                        self.wfile.write(body)
                    except Exception as e:
                        self.send_response(502)
                        self.end_headers()
                        self.wfile.write(f'ERR: {repr(e)}'.encode())
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'cam_id not in PAGE_URLS')
            else:
                self.send_response(404)
                self.end_headers()
            return

        # Default response
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        html = f'<html><body><h1>SkylineWebcams HLS Proxy</h1>'
        html += f'<p>Cams: {len(TOKENS)} ({sum(1 for v in TOKENS.values() if v.get("live"))} live)</p>'
        html += f'<p>Try: /skyline/998/stream.m3u8</p>'
        html += '</body></html>'
        self.wfile.write(html.encode())


def main():
    load_tokens()
    print(f'Loaded {len(TOKENS)} tokens', flush=True)
    server = ThreadingHTTPServer(('0.0.0.0', 8771), Handler)
    print(f'SkylineWebcams HLS proxy listening on :8771', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()