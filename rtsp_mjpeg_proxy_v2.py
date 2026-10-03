"""RTSP-to-MJPEG proxy v2 with more auth variants and stream management.

Reads stream list from rtsp_proxy_streams.json, exposes:
- /list: list of all streams
- /stream/<id>: MJPEG multipart stream
- /snapshot/<id>: single JPEG snapshot
- /health: health check
"""
import json
import time
import threading
import socket
import struct
import base64
import cv2
import numpy as np
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


STREAMS_FILE = 'rtsp_proxy_streams.json'
STREAMS = {}


def load_streams():
    global STREAMS
    try:
        with open(STREAMS_FILE, 'r') as f:
            data = json.load(f)
        STREAMS = data
        print(f'[RTSP-MJPEG] Loaded {len(STREAMS)} streams', flush=True)
    except Exception as e:
        print(f'[RTSP-MJPEG] Load err: {e}', flush=True)
        STREAMS = {}


# Per-stream worker that captures latest frame
class StreamWorker:
    def __init__(self, stream_id, url, ip, port, path, creds):
        self.stream_id = stream_id
        self.url = url
        self.ip = ip
        self.port = port
        self.path = path
        self.creds = creds
        self.latest_jpeg = None
        self.lock = threading.Lock()
        self.last_update = 0
        self.fps = 0
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while self.running:
            try:
                cap = cv2.VideoCapture(self.url)
                if not cap.isOpened():
                    time.sleep(5)
                    continue
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                n_frames = 0
                t0 = time.time()
                while self.running:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    # Encode as JPEG
                    _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    with self.lock:
                        self.latest_jpeg = jpeg.tobytes()
                        self.last_update = time.time()
                    n_frames += 1
                    if n_frames >= 30:
                        self.fps = n_frames / (time.time() - t0)
                        n_frames = 0
                        t0 = time.time()
                cap.release()
            except Exception as e:
                pass
            time.sleep(2)

    def get_frame(self):
        with self.lock:
            if self.latest_jpeg:
                return self.latest_jpeg
        return None

    def is_fresh(self, max_age=10):
        return (time.time() - self.last_update) < max_age


# Active workers
WORKERS = {}


def start_workers():
    global WORKERS
    for sid, info in STREAMS.items():
        if sid in WORKERS:
            continue
        try:
            w = StreamWorker(sid, info['url'], info['ip'], info['port'], info['path'], info['creds'])
            WORKERS[sid] = w
        except Exception as e:
            print(f'  Worker {sid} err: {e}')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Silent

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            data = {
                'status': 'ok',
                'streams': len(WORKERS),
                'fresh': sum(1 for w in WORKERS.values() if w.is_fresh()),
            }
            self.wfile.write(json.dumps(data).encode())
            return

        if path == '/list':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            data = []
            for sid, w in WORKERS.items():
                data.append({
                    'id': sid,
                    'url': w.url,
                    'fresh': w.is_fresh(),
                    'fps': round(w.fps, 2),
                    'last_update': w.last_update,
                })
            self.wfile.write(json.dumps(data, indent=2).encode())
            return

        if path.startswith('/stream/'):
            sid = path[8:]
            if sid not in WORKERS:
                self.send_error(404, f'Stream {sid} not found')
                return
            w = WORKERS[sid]
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                while True:
                    frame = w.get_frame()
                    if frame:
                        self.wfile.write(b'--frame\r\n')
                        self.wfile.write(b'Content-Type: image/jpeg\r\n')
                        self.wfile.write(f'Content-Length: {len(frame)}\r\n\r\n'.encode())
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                    time.sleep(0.1)
            except Exception:
                pass
            return

        if path.startswith('/snapshot/'):
            sid = path[10:]
            if sid not in WORKERS:
                self.send_error(404, f'Stream {sid} not found')
                return
            w = WORKERS[sid]
            frame = w.get_frame()
            if frame:
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(frame)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(frame)
            else:
                self.send_error(503, 'No frame yet')
            return

        if path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            html = f'''<!DOCTYPE html>
<html><head><title>RTSP-MJPEG Proxy v2</title></head>
<body>
<h1>RTSP-MJPEG Proxy v2</h1>
<p>{len(WORKERS)} streams</p>
<p>Endpoints:</p>
<ul>
<li><a href="/list">/list</a> - JSON list of streams</li>
<li><a href="/health">/health</a> - Health check</li>
<li>/stream/&lt;id&gt; - MJPEG stream</li>
<li>/snapshot/&lt;id&gt; - single JPEG</li>
</ul>
<h2>Streams:</h2>
<table border=1>
<tr><th>ID</th><th>URL</th><th>Fresh</th><th>FPS</th><th>Snapshot</th><th>Stream</th></tr>
'''
            for sid, w in WORKERS.items():
                html += f'<tr><td>{sid}</td><td>{w.url}</td><td>{"✓" if w.is_fresh() else "✗"}</td><td>{w.fps:.1f}</td>'
                html += f'<td><a href="/snapshot/{sid}">snap</a></td><td><a href="/stream/{sid}">stream</a></td></tr>\n'
            html += '</table></body></html>'
            self.wfile.write(html.encode())
            return

        self.send_error(404)


def main():
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f'[RTSP-MJPEG v2] CWD: {os.getcwd()}', flush=True)
    print('[RTSP-MJPEG v2] Starting on port 8768...', flush=True)
    load_streams()
    start_workers()
    print(f'[RTSP-MJPEG v2] Started {len(WORKERS)} workers', flush=True)
    server = ThreadingHTTPServer(('0.0.0.0', 8768), Handler)
    print('[RTSP-MJPEG v2] Listening on :8768', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
