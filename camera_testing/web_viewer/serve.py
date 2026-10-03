"""Start a local HTTP server for the CSV viewer.

Serves:
- http://localhost:8765/         -> webcam DB viewer (index.html)
- http://localhost:8765/csv      -> raw CSV (streamed)
- http://localhost:8765/db.sqlite -> SQLite DB
- http://localhost:8765/viewer    -> alternative viewer

Runs in background. To stop: kill the python process.
"""
import os
import sys
import http.server
import socketserver
import threading

PORT = 8765
WEB_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\web_viewer'
CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)
    def log_message(self, format, *args):
        pass  # quiet
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


def run():
    os.chdir(WEB_DIR)
    with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
        httpd.serve_forever()


if __name__ == '__main__':
    run()
