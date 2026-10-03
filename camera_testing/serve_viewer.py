"""Start a local HTTP server for the CSV viewer.

Serves:
- http://localhost:8765/                  -> webcam DB viewer (index.html)
- http://localhost:8765/controllable_Webcams.csv -> raw CSV (streamed, with no-store cache)
- http://localhost:8765/webcams.db        -> SQLite DB
- http://localhost:8765/csv_chunks/       -> per-chunk CSV files
"""
import os
import sys
import http.server
import socketserver
import mimetypes

PORT = 8765
ROOT_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance'


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT_DIR, **kwargs)

    def log_message(self, format, *args):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        # Range requests for video/audio preview
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def guess_type(self, path):
        # Force text/html for the viewer
        if path.endswith('.html') or path.endswith('.htm'):
            return 'text/html'
        ctype, _ = mimetypes.guess_type(path)
        if ctype is None:
            if path.endswith('.csv'):
                return 'text/csv'
            if path.endswith('.db'):
                return 'application/octet-stream'
        return ctype or 'application/octet-stream'


def run():
    os.chdir(ROOT_DIR)
    with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
        httpd.serve_forever()


if __name__ == '__main__':
    run()
