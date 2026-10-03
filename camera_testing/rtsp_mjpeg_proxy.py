"""RTSP-to-MJPEG proxy server.

Transcodes RTSP H.264 streams to MJPEG multipart for browser viewing.

Uses:
- opencv-python for RTSP demuxing + JPEG encoding
- PIL for JPEG output
- Threading for concurrent client handling

Routes:
- /health - health check
- /list - list of available streams
- /stream/<id> - MJPEG proxy for a stream
- /snapshot/<id> - single JPEG snapshot
"""

import os
import sys
import csv
import json
import time
import threading
import signal
import socketserver
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Try to import opencv
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("WARNING: opencv-python not available. RTSP proxy will not work.")


WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
PORT = 8768

# Stream cache: stream_id -> Thread + latest frame
streams = {}
streams_lock = threading.Lock()

# Track failures
fail_count = {}


def load_streams():
    """Load all RTSP streams from master CSV."""
    csv.field_size_limit(2**31 - 1)
    streams_list = []
    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url", "")
            live_url = row.get("live_stream_url", "")
            rtsp_url = live_url if "rtsp://" in (live_url or "") else (url if "rtsp://" in (url or "") else "")
            if rtsp_url:
                streams_list.append({
                    "id": f"{len(streams_list)}",
                    "host": url.split(":")[1].replace("//", "") if "://" in url else url,
                    "port": 554,
                    "rtsp_url": rtsp_url,
                    "brand": row.get("brand", ""),
                    "country": row.get("country", ""),
                    "description": row.get("description", "")[:80],
                })
    return streams_list


def capture_thread(stream):
    """Background thread that captures RTSP frames and stores latest JPEG."""
    if not CV2_AVAILABLE:
        return
    stream_id = stream["id"]
    rtsp_url = stream["rtsp_url"]
    fail_count[stream_id] = 0

    # Try auth variants for this RTSP URL
    auth_urls = [
        rtsp_url,  # No auth
        rtsp_url.replace("rtsp://", "rtsp://admin:admin@"),
        rtsp_url.replace("rtsp://", "rtsp://admin:12345@"),
        rtsp_url.replace("rtsp://", "rtsp://admin:password@"),
        rtsp_url.replace("rtsp://", "rtsp://admin:1234@"),
        rtsp_url.replace("rtsp://", "rtsp://admin:@"),
        rtsp_url.replace("rtsp://", "rtsp://root:root@"),
        rtsp_url.replace("rtsp://", "rtsp://user:user@"),
        rtsp_url.replace("rtsp://", "rtsp://viewer1:viewer@"),
        rtsp_url.replace("rtsp://", "rtsp://admin:changeme@"),
    ]

    for try_url in auth_urls:
        if stream_id not in streams:
            break
        try:
            cap = cv2.VideoCapture(try_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not cap.isOpened():
                cap.release()
                continue
            stream["working_url"] = try_url
            while stream_id in streams:
                ret, frame = cap.read()
                if not ret:
                    fail_count[stream_id] += 1
                    break
                # Encode as JPEG
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                with streams_lock:
                    if stream_id in streams:
                        streams[stream_id]["latest_jpeg"] = jpeg.tobytes()
                        streams[stream_id]["last_update"] = time.time()
            cap.release()
            if stream_id not in streams:
                break
            # If we got at least one frame, we succeeded - no need to try other creds
            with streams_lock:
                if stream_id in streams and streams[stream_id]["latest_jpeg"]:
                    break
        except Exception as e:
            try:
                cap.release()
            except: pass
            fail_count[stream_id] += 1
            continue
    # Remove dead stream
    with streams_lock:
        if stream_id in streams:
            del streams[stream_id]


def start_stream(stream):
    """Start capture thread for a stream."""
    stream_id = stream["id"]
    with streams_lock:
        if stream_id not in streams:
            streams[stream_id] = {
                "info": stream,
                "latest_jpeg": None,
                "last_update": 0,
            }
            t = threading.Thread(target=capture_thread, args=(stream,), daemon=True)
            t.start()


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logging

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            status = {
                "opencv": CV2_AVAILABLE,
                "streams": len(streams),
                "active": sum(1 for s in streams.values() if s["latest_jpeg"]),
            }
            self.wfile.write(json.dumps(status).encode())

        elif path == "/list":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            stream_data = []
            for sid, s in streams.items():
                info = s["info"]
                stream_data.append({
                    "id": sid,
                    "host": info["host"],
                    "rtsp_url": info["rtsp_url"],
                    "brand": info["brand"],
                    "country": info["country"],
                    "description": info["description"],
                    "active": s["latest_jpeg"] is not None,
                    "last_update": s["last_update"],
                })
            self.wfile.write(json.dumps({"streams": stream_data}, indent=2).encode())

        elif path.startswith("/stream/"):
            stream_id = path.split("/")[2]
            self.handle_stream(stream_id)

        elif path.startswith("/snapshot/"):
            stream_id = path.split("/")[2]
            self.handle_snapshot(stream_id)

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")

    def handle_stream(self, stream_id):
        """Stream MJPEG to client."""
        if stream_id not in streams:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        last_frame_time = 0
        while stream_id in streams:
            with streams_lock:
                jpeg_data = streams[stream_id].get("latest_jpeg")
                last_update = streams[stream_id].get("last_update", 0)
            if jpeg_data and last_update != last_frame_time:
                try:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpeg_data)}\r\n\r\n".encode())
                    self.wfile.write(jpeg_data)
                    self.wfile.write(b"\r\n")
                    last_frame_time = last_update
                except (BrokenPipeError, ConnectionResetError):
                    break
            time.sleep(0.05)

    def handle_snapshot(self, stream_id):
        """Return single JPEG."""
        if stream_id not in streams:
            self.send_response(404)
            self.end_headers()
            return
        with streams_lock:
            jpeg_data = streams[stream_id].get("latest_jpeg")
        if not jpeg_data:
            self.send_response(503)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg_data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(jpeg_data)


def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"[RTSP->MJPEG Proxy] Loading streams from {MASTER_CSV}")
    if not CV2_AVAILABLE:
        print("[RTSP->MJPEG Proxy] opencv-python NOT installed. Install with: pip install opencv-python")
        print("[RTSP->MJPEG Proxy] Proxy will run in stub mode (no actual transcoding).")
    stream_list = load_streams()
    print(f"[RTSP->MJPEG Proxy] Found {len(stream_list)} RTSP streams")

    # Start capture threads
    for stream in stream_list:
        start_stream(stream)

    # Start HTTP server
    class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = ThreadedHTTPServer(("0.0.0.0", PORT), ProxyHandler)
    print(f"[RTSP->MJPEG Proxy] Listening on port {PORT}")

    def signal_handler(sig, frame):
        print("\n[RTSP->MJPEG Proxy] Shutting down...")
        server.shutdown()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
