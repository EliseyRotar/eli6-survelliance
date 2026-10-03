"""Canon VB WV-HTTP MJPEG stream proxy - REWRITTEN.

Forwards WV-HTTP multipart MJPEG streams from /-wvhttp-01-/video
to browsers via standard multipart/x-mixed-replace MJPEG.

Routes:
  GET /mjpeg/<host>/<port>/<size>/native   - native multipart from WV-HTTP /video (10fps)
  GET /mjpeg/<host>/<port>/<size>         - polling-based (1-3 fps)
  GET /snapshot/<host>/<port>/<size>      - single JPEG snapshot
  GET /health                              - health check
  GET /list                                - list live cams
"""

import os
import re
import time
import json
import threading
import socket
import urllib3
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PORT = 8767


# Session pool (no requests lib - use raw sockets)
class WVSessionPool:
    def __init__(self, timeout=300):
        self.sessions = {}
        self.timeout = timeout
        self.lock = threading.Lock()

    def get_session(self, host, port, size):
        key = (host, port, size)
        now = time.time()
        with self.lock:
            if key in self.sessions:
                sid, exp = self.sessions[key]
                if exp > now:
                    return sid
        # Open new session via raw HTTP
        try:
            sock = socket.create_connection((host, port), timeout=5)
            req = f'GET /-wvhttp-01-/open.cgi?seq={int(time.time()*1000)%100000}&priority=0&v=h264:{size} HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
            sock.send(req.encode())
            buf = b''
            while b'\r\n\r\n' not in buf:
                d = sock.recv(1024)
                if not d:
                    sock.close()
                    return None
                buf += d
            body_start = buf.find(b'\r\n\r\n') + 4
            body = buf[body_start:]
            while b's:=' not in body and len(body) < 200:
                try:
                    d = sock.recv(1024)
                    if not d:
                        break
                    body += d
                except socket.timeout:
                    break
            sock.close()
            m = re.search(rb's:=([0-9a-f-]+)', body)
            if m:
                sid = m.group(1).decode()
                with self.lock:
                    self.sessions[key] = (sid, now + self.timeout)
                return sid
        except Exception:
            pass
        return None


SESSION_POOL = WVSessionPool()


def proxy_native_stream(handler, host, port, sid):
    """Forward native WV-HTTP multipart stream directly."""
    try:
        sock = socket.create_connection((host, port), timeout=10)
        req = f'GET /-wvhttp-01-/video?{sid}&seq=1 HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        # Read header
        buf = b''
        while b'\r\n\r\n' not in buf:
            d = sock.recv(1)
            if not d:
                sock.close()
                return
            buf += d
        # Body is everything after \r\n\r\n
        body_start = buf.find(b'\r\n\r\n') + 4
        # We need to rewrite the boundary to match what we declared
        # The upstream uses `--boundary`, we declared `boundary=--vbframe`
        # So replace `--boundary` with `--vbframe` in the forwarded body
        if body_start < len(buf):
            chunk_to_send = buf[body_start:].replace(b'--boundary', b'--vbframe')
            handler.wfile.write(chunk_to_send)
            handler.wfile.flush()
        # Now stream the rest
        while True:
            try:
                chunk = sock.recv(16384)
                if not chunk:
                    break
                chunk = chunk.replace(b'--boundary', b'--vbframe')
                handler.wfile.write(chunk)
                handler.wfile.flush()
            except (socket.timeout, BrokenPipeError, ConnectionResetError):
                break
        sock.close()
    except Exception as e:
        print(f'[NATIVE] Error: {e}', flush=True)


def proxy_polling_stream(handler, host, port, size):
    """Poll image.cgi and forward as MJPEG. ~1-2 fps."""
    boundary = b'--vbframe\r\n'
    seq = 0
    while True:
        try:
            sock = socket.create_connection((host, port), timeout=5)
            req = f'GET /-wvhttp-01-/image.cgi?v=jpg:{size}&seq={seq} HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
            sock.send(req.encode())
            buf = b''
            while b'\r\n\r\n' not in buf:
                d = sock.recv(1)
                if not d:
                    break
                buf += d
            if b'\r\n\r\n' not in buf:
                sock.close()
                seq += 1
                time.sleep(0.1)
                continue
            body_start = buf.find(b'\r\n\r\n') + 4
            body = buf[body_start:]
            # Try to read full content-length if specified
            cl_m = re.search(rb'Content-Length: (\d+)', buf, re.I)
            if cl_m:
                cl = int(cl_m.group(1))
                while len(body) < cl:
                    try:
                        d = sock.recv(8192)
                        if not d:
                            break
                        body += d
                    except socket.timeout:
                        break
            sock.close()

            # Verify JPEG
            if b'\xff\xd8\xff' not in body[:20]:
                seq += 1
                time.sleep(0.1)
                continue

            # Wrap as multipart frame
            frame = boundary
            frame += b'Content-Type: image/jpeg\r\n'
            frame += f'Content-Length: {len(body)}\r\n'.encode()
            frame += b'\r\n'
            frame += body
            frame += b'\r\n'
            handler.wfile.write(frame)
            handler.wfile.flush()
            seq += 1
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            time.sleep(0.2)
            continue


def fetch_snapshot(host, port, size):
    """Fetch a single JPEG snapshot via raw socket."""
    try:
        sock = socket.create_connection((host, port), timeout=5)
        req = f'GET /-wvhttp-01-/image.cgi?v=jpg:{size} HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            d = sock.recv(1)
            if not d:
                break
            buf += d
        body_start = buf.find(b'\r\n\r\n') + 4
        body = buf[body_start:]
        cl_m = re.search(rb'Content-Length: (\d+)', buf, re.I)
        if cl_m:
            cl = int(cl_m.group(1))
            while len(body) < cl:
                try:
                    d = sock.recv(8192)
                    if not d:
                        break
                    body += d
                except socket.timeout:
                    break
        sock.close()
        if b'\xff\xd8\xff' in body[:20]:
            return body
    except Exception:
        pass
    return None


class MJPEGHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        path = self.path
        parsed = urlparse(path)

        if path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'sessions': len(SESSION_POOL.sessions)}).encode())
            return

        if path == '/list':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            cams = []
            csv_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams_vbviewer.csv'
            if os.path.exists(csv_path):
                import csv as csvmod
                with open(csv_path, 'r', encoding='utf-8', errors='replace', newline='') as f:
                    csvmod.field_size_limit(2**31 - 1)
                    reader = csvmod.DictReader(f)
                    for row in reader:
                        host = (row.get('host') or '').strip()
                        url = (row.get('url') or '').strip()
                        live = (row.get('live_status') or '').strip()
                        type_ = (row.get('type') or '').strip()
                        if host and live == 'live':
                            # Validate host looks like IP or hostname (no spaces)
                            if ' ' not in host and len(host) < 255:
                                cams.append({'host': host, 'url': url, 'type': type_})
            self.wfile.write(json.dumps({'cams': cams[:500]}).encode())
            return

        # Match /mjpeg/<host>/<port>/<size>[/native]
        m = re.match(r'^/mjpeg/([^/]+)/(\d+)/([^/]+)(?:/(native))?/?$', path)
        if m:
            host = m.group(1)
            port = int(m.group(2))
            size = m.group(3)
            native = bool(m.group(4))

            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=--vbframe')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            try:
                if native:
                    sid = SESSION_POOL.get_session(host, port, size)
                    if not sid:
                        return
                    proxy_native_stream(self, host, port, sid)
                else:
                    proxy_polling_stream(self, host, port, size)
            except Exception:
                pass
            return

        # Match /snapshot/<host>/<port>/<size>
        m = re.match(r'^/snapshot/([^/]+)/(\d+)/([^/]+)/?$', path)
        if m:
            host = m.group(1)
            port = int(m.group(2))
            size = m.group(3)
            frame = fetch_snapshot(host, port, size)
            if frame:
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(frame)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(frame)
            else:
                self.send_response(502)
                self.end_headers()
            return

        # 404
        self.send_response(404)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>404</h1>')


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    wbufsize = 0


def main():
    server = ThreadingHTTPServer(('0.0.0.0', PORT), MJPEGHandler)
    print(f'[VB MJPEG Proxy] Listening on 0.0.0.0:{PORT}', flush=True)
    print(f'  Routes:', flush=True)
    print(f'    /mjpeg/<host>/<port>/<size>/native - native WV-HTTP multipart (10fps)', flush=True)
    print(f'    /mjpeg/<host>/<port>/<size>         - polling-based MJPEG (1-2fps)', flush=True)
    print(f'    /snapshot/<host>/<port>/<size>      - single JPEG snapshot', flush=True)
    print(f'    /list                                - list of live cams', flush=True)
    print(f'    /health                              - health check', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.shutdown()


if __name__ == '__main__':
    main()
