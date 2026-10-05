"""Tiny localhost receiver: POST /save/<name> writes body to camera_testing/<name>.

Used by Playwright scraper to persist chunks without returning bulk JSON.
Bind 127.0.0.1 only; name sanitized to [A-Za-z0-9._-].
"""
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

DEST = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing'
PORT = 8799
NAME_RE = re.compile(r'^[A-Za-z0-9._-]{1,80}$')


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if not self.path.startswith('/save/'):
            self.send_response(404)
            self.end_headers()
            return
        name = self.path[len('/save/'):]
        if not NAME_RE.match(name) or not name.endswith('.json'):
            self.send_response(400)
            self.end_headers()
            return
        n = int(self.headers.get('Content-Length') or 0)
        if n > 20 * 1024 * 1024:
            self.send_response(413)
            self.end_headers()
            return
        body = self.rfile.read(n)
        with open(os.path.join(DEST, name), 'wb') as f:
            f.write(body)
        self.send_response(200)
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b'OK')

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b'OK')

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    HTTPServer(('127.0.0.1', PORT), H).serve_forever()
