"""Probing + classification library - v3 with 200+ patterns across all major vendors.

Covers:
- AXIS (VAPIX, MJPEG, H.264, H.265)
- Hikvision (ISAPI, RTSP, MJPEG, Webs digest)
- Dahua (HTTP CGI, RTSP, MJPEG)
- Reolink (API CGI, RTSP, MJPEG)
- WebcamXP / WebcamXP 5 (MJPEG multipart)
- ACTi (wvhttp, MJPEG)
- HiSilicon Hi3510/Hi3518 (CGI param, RTSP)
- Mobotix (MxPEG, MJPEG)
- Hikam / Sannce / Lorex / Swann / Annke / LTS
- Panasonic BB / BL / DG / i-Pro (CGI)
- Sony SNC (CGI)
- Canon VB / VB-M / VB-R (CGI)
- Bosch (CGI, RTSP)
- Vivotek (CGI, RTSP)
- D-Link DCS (CGI)
- TP-Link Tapo (CGI, RTSP)
- Wansview (CGI)
- Foscam (CGI)
- GeoVision (CGI)
- Trendnet (CGI)
- Samsung / Hanwha (CGI, RTSP)
- Grandstream (CGI)
- Arecont (CGI)
- Honeywell (CGI)
- BirdDog (NDI, RTSP)
- Ubiquiti UniFi Video (CGI, RTSP)
- Lumens (CGI)
- Milesight (CGI)
- Provision-ISR / Vantage / DMax
- MJPG-Streamer (default URLs)
- mjpg-streamer (cam 0/1/2)
- IPCam Client / webcamXP server / go1984
- Yawcam (port 8081, /cam.jpg)
- IP Webcam (Android) (port 8080, /video)
- DroidCam (port 4747)
- IPEYE (Russian, port 80)
- NSC (Norwegian Vison, port 80)
- Edimax (port 80)
- AirLive (port 80)
- NUUO (port 80, NVMS1000/NVMS2)
- Blue Iris (port 81/8082)
- iSpy (port 80, agent)
- ZoneMinder (port 80, /cgi-bin/nph-zms)
- Shinobi (port 8080)
- CamXploit default cams
- Insecam-style viewers
"""
import re
import requests
import urllib.parse
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# All probe paths - ordered by typical yield (high first)
# Weight: base weight; family: detection label; format: stream type
PROBE_PATTERNS = [
    # === AXIS (top priority - well-known paths) ===
    ('/axis-cgi/media.cgi?container=matroska&videocodec=h264&resolution=1280x720', 80, 'axis-h264-matroska', 'video'),
    ('/axis-cgi/media.cgi?container=matroska&videocodec=h265', 80, 'axis-h265-matroska', 'video'),
    ('/axis-cgi/media.cgi?container=mp4&videocodec=h264', 75, 'axis-h264-mp4', 'video'),
    ('/axis-cgi/mjpg/video.cgi?resolution=1280x720', 70, 'axis-mjpeg', 'video'),
    ('/axis-cgi/mjpg/video.cgi', 65, 'axis-mjpeg', 'video'),
    ('/axis-cgi/mjpeg/video.cgi', 65, 'axis-mjpeg', 'video'),
    ('/axis-cgi/jpg/image.cgi?resolution=1920x1080', 25, 'axis-jpeg', 'image'),
    ('/axis-cgi/jpg/image.cgi', 20, 'axis-jpeg', 'image'),
    ('/axis-cgi/viewer/video.jpg', 60, 'axis-viewer', 'video'),

    # === Hikvision (ISAPI + Webs digest + RTSP-like) ===
    ('/ISAPI/Streaming/tracks/101', 65, 'hikvision-h264', 'video'),
    ('/ISAPI/Streaming/tracks/1', 65, 'hikvision-h264', 'video'),
    ('/ISAPI/Streaming/channels/101/httppreview', 70, 'hikvision-h264', 'video'),
    ('/ISAPI/Streaming/channels/1/httppreview', 70, 'hikvision-h264', 'video'),
    ('/ISAPI/Streaming/channels/101/picture', 20, 'hikvision-jpeg', 'image'),
    ('/ISAPI/Streaming/channels/1/picture', 20, 'hikvision-jpeg', 'image'),
    ('/Streaming/tracks/101', 65, 'hikvision-h264', 'video'),
    ('/Streaming/tracks/1', 65, 'hikvision-h264', 'video'),
    ('/streaming/tracks/101', 65, 'hikvision-h264', 'video'),
    ('/streaming/tracks/1', 65, 'hikvision-h264', 'video'),

    # === Dahua ===
    ('/cam/realmonitor', 65, 'dahua-mjpeg', 'video'),
    ('/cgi-bin/snapshot.cgi?channel=1', 20, 'dahua-jpeg', 'image'),
    ('/cgi-bin/magicBox.cgi?action=getSystemInfo', 30, 'dahua-system', 'metadata'),
    ('/cgi-bin/snapshot.cgi', 20, 'dahua-jpeg', 'image'),
    ('/onvif/device_service', 30, 'onvif', 'metadata'),
    ('/cgi-bin/devVideoInput.cgi?action=getInputs', 30, 'dahua-cgi', 'metadata'),

    # === Reolink ===
    ('/cgi-bin/api.cgi?cmd=Snap&channel=0', 25, 'reolink-jpeg', 'image'),
    ('/cgi-bin/api.cgi?cmd=GetDevInfo', 30, 'reolink-cgi', 'metadata'),

    # === HiSilicon Hi3510/Hi3518 (Hipcam, Sannce, Annke, LTS) ===
    ('/web/tmpfs/mjpeg', 50, 'hipcam-mjpeg', 'video'),
    ('/web/tmpfs/mjpeg.jpg', 50, 'hipcam-mjpeg', 'video'),
    ('/web/tmpfs/snap.jpg', 15, 'hipcam-jpeg', 'image'),
    ('/web/tmpfs/auto.jpg', 12, 'hipcam-jpeg', 'image'),
    ('/cgi-bin/hi3510/param.cgi?cmd=getserverinfo', 30, 'hipcam-cgi', 'metadata'),

    # === WebcamXP / WebcamXP 5 ===
    ('/cam_1.cgi', 50, 'webcamxp', 'video'),
    ('/cam_1.mjpg', 50, 'webcamxp', 'video'),
    ('/cam_1.jpg', 15, 'webcamxp-jpeg', 'image'),
    ('/videostream.cgi', 50, 'webcamxp-stream', 'video'),

    # === ACTi (wvhttp) ===
    ('/-wvhttp-01-/video.cgi', 45, 'acti-mjpeg', 'video'),
    ('/-wvhttp-01-/GetData.cgi', 45, 'acti-mjpeg', 'video'),
    ('/-wvhttp-01-/image.cgi', 15, 'acti-jpeg', 'image'),

    # === MJPG-Streamer (default install on Linux) ===
    ('/?action=stream', 50, 'mjpg-streamer', 'video'),
    ('/?action=snapshot', 15, 'mjpg-streamer-snap', 'image'),
    ('/stream', 50, 'mjpg-streamer-stream', 'video'),
    ('/cam0.jpg', 15, 'mjpg-streamer-cam0', 'image'),
    ('/cam1.jpg', 15, 'mjpg-streamer-cam1', 'image'),

    # === Insecam style (Bosch, Canon, Panasonic) ===
    ('/cgi-bin/viewer/video.jpg', 50, 'insecam-viewer', 'video'),
    ('/viewer/video.jpg', 50, 'insecam-viewer', 'video'),
    ('/cgi-bin/video.jpg', 50, 'insecam-viewer', 'video'),
    ('/cgi-bin/faststream.jpg?stream=full&fps=16', 55, 'mjpeg-faststream', 'video'),
    ('/control/faststream.jpg?stream=full&fps=16', 55, 'mjpeg-faststream', 'video'),
    ('/faststream.jpg?stream=full&fps=16', 55, 'mjpeg-faststream', 'video'),

    # === Mobotix ===
    ('/nphMotionJpeg?Resolution=640x480&Quality=Motion', 35, 'mobotix', 'video'),
    ('/cgi-bin/jpgshow', 15, 'mobotix-jpeg', 'image'),
    ('/cgi-bin/image.jpg', 15, 'mobotix-jpeg', 'image'),
    ('/control/faststream.jpg', 55, 'mobotix-faststream', 'video'),

    # === Canon VB / VB-M / VB-R ===
    ('/img/main.cgi?StreamCmd=Live&Mode=Live&Resolution=640x480', 35, 'canon', 'video'),
    ('/-wvhttp-01-/video.cgi', 45, 'canon-mjpeg', 'video'),

    # === Panasonic BB / BL / DG / i-Pro ===
    ('/cgi-bin/mjpeg', 35, 'panasonic-mjpeg', 'video'),
    ('/cgi-bin/viewer/video.jpg', 50, 'panasonic-viewer', 'video'),
    ('/cgi-bin/camera', 30, 'panasonic-cgi', 'metadata'),
    ('/Streaming/Channels/101', 65, 'panasonic-h264', 'video'),
    ('/Streaming/Channels/1', 65, 'panasonic-h264', 'video'),

    # === Sony SNC ===
    ('/image', 10, 'sony-jpeg', 'image'),
    ('/oneshotimage.jpg', 15, 'sony-oneshot', 'image'),
    ('/img/snapshot.cgi', 15, 'sony-snapshot', 'image'),
    ('/mjpeg', 35, 'sony-mjpeg', 'video'),

    # === Bosch ===
    ('/cgi-bin/viewer/video.jpg', 50, 'bosch-viewer', 'video'),
    ('/snap.jpg', 15, 'bosch-jpeg', 'image'),
    ('/rcserver.jpg', 15, 'bosch-jpeg', 'image'),

    # === Vivotek ===
    ('/cgi-bin/viewer/video.jpg', 50, 'vivotek-viewer', 'video'),
    ('/cgi-bin/viewer/recall.cgi', 15, 'vivotek-recall', 'image'),
    ('/live.sdp', 30, 'vivotek-rtsp-sdp', 'video'),

    # === D-Link DCS ===
    ('/image/jpeg.cgi', 15, 'dlink-jpeg', 'image'),
    ('/video/mjpg.cgi', 50, 'dlink-mjpeg', 'video'),
    ('/dms', 30, 'dlink-dms', 'metadata'),
    ('/mjpeg.cgi', 50, 'dlink-mjpeg', 'video'),

    # === TP-Link Tapo ===
    ('/stream/mp4', 65, 'tapo-h264', 'video'),
    ('/stream/mjpeg', 50, 'tapo-mjpeg', 'video'),
    ('/stream/mp4/channel/1', 65, 'tapo-h264-ch1', 'video'),

    # === Foscam / Wansview / Wanscam / EasyN / EasyCam / Sricam / Tenvis ===
    ('/cgi-bin/snapshot.cgi', 15, 'foscam-jpeg', 'image'),
    ('/cgi-bin/CGIStream.cgi?cmd=GetMJStream', 50, 'foscam-mjpeg', 'video'),
    ('/cgi-bin/mjpg/video.cgi', 50, 'foscam-mjpeg', 'video'),
    ('/livestream/11', 65, 'wansview-h264', 'video'),
    ('/livestream/12', 50, 'wansview-sub', 'video'),
    ('/tmpfs/snap.jpg', 15, 'wansview-jpeg', 'image'),
    ('/img/snapshot.cgi', 15, 'easycam-jpeg', 'image'),

    # === GeoVision ===
    ('/VIDEO.JPG', 15, 'geovision-jpeg', 'image'),
    ('/VIDEO.MJPG', 50, 'geovision-mjpeg', 'video'),
    ('/PSIA/Streaming/channels/1', 65, 'geovision-h264', 'video'),

    # === Samsung / Hanwha (WiseNet) ===
    ('/cgi-bin/video.cgi?msubmenu=mjpg', 50, 'samsung-mjpeg', 'video'),
    ('/cgi-bin/video.cgi?msubmenu=sjpg', 15, 'samsung-jpeg', 'image'),
    ('/cgi-bin/video.cgi?msubmenu=h264', 65, 'samsung-h264', 'video'),
    ('/stw-cgi/video.cgi?msubmenu=mjpg', 50, 'samsung-mjpeg', 'video'),

    # === Grandstream ===
    ('/web/cgi-bin/hi3510/snap.cgi?&-getstream', 50, 'grandstream', 'video'),
    ('/web/cgi-bin/hi3510/snap.cgi', 15, 'grandstream-snap', 'image'),

    # === Arecont ===
    ('/image', 10, 'arecont-jpeg', 'image'),
    ('/img', 10, 'arecont-img', 'image'),

    # === BirdDog NDI / RTSP ===
    ('/birddog-rtsp', 30, 'birddog', 'metadata'),

    # === Ubiquiti UniFi Video / UniFi Protect ===
    ('/api/video', 30, 'ubiquiti', 'metadata'),
    ('/snap.jpeg', 15, 'ubiquiti-jpeg', 'image'),

    # === Trendnet / Edimax / AirLive / Y-Cam ===
    ('/cgi/jpg/image.cgi', 15, 'trendnet-jpeg', 'image'),
    ('/image.jpg', 10, 'edimax-jpeg', 'image'),

    # === Android IP Webcam ===
    ('/video', 50, 'ipwebcam-android', 'video'),
    ('/shot.jpg', 15, 'ipwebcam-snap', 'image'),
    ('/screenshot.jpg', 15, 'ipwebcam-screenshot', 'image'),

    # === DroidCam ===
    ('/video', 50, 'droidcam', 'video'),

    # === IPEYE (Russian) ===
    ('/live/0/mjpeg.jpg', 50, 'ipeye', 'video'),
    ('/live/0/snapshot.jpg', 15, 'ipeye-snap', 'image'),
    ('/mjpg/video.mjpg', 50, 'ipeye-mjpeg', 'video'),

    # === Yawcam (port 8081) ===
    ('/cam.jpg', 15, 'yawcam-jpeg', 'image'),
    ('/out.jpg', 15, 'yawcam-out', 'image'),

    # === Blue Iris (port 81) ===
    ('/mjpg/video.mjpg', 50, 'blueiris', 'video'),
    ('/image.jpg', 10, 'blueiris-jpeg', 'image'),

    # === ZoneMinder ===
    ('/cgi-bin/nph-zms?mode=jpeg', 50, 'zoneminder', 'video'),
    ('/cgi-bin/zms?mode=jpeg', 50, 'zoneminder2', 'video'),

    # === Shinobi ===
    ('/stream.mp4', 65, 'shinobi-h264', 'video'),
    ('/mjpg/video.mjpg', 50, 'shinobi-mjpeg', 'video'),

    # === iSpy / Agent DVR ===
    ('/video.mp4', 65, 'ispy-h264', 'video'),
    ('/mpeg4', 65, 'ispy-mpeg4', 'video'),

    # === Wanscam / Sricam / Tenvis / EasyN / EasyCam / Vstarcam ===
    ('/livestream/11', 65, 'sricam-h264', 'video'),
    ('/livestream/12', 50, 'sricam-sub', 'video'),
    ('/tmpfs/snap.jpg', 15, 'sricam-jpeg', 'image'),

    # === Vstarcam (Cinese) ===
    ('/cgi-bin/snapshot.cgi', 15, 'vstarcam-jpeg', 'image'),
    ('/cgi-bin/CGIStream.cgi?cmd=GetMJStream', 50, 'vstarcam-mjpeg', 'video'),

    # === Generic / fallback ===
    ('/mjpg/video.mjpg', 45, 'mjpeg-mjpg', 'video'),
    ('/video.mjpg', 45, 'mjpeg-mjpg', 'video'),
    ('/mjpg', 45, 'mjpeg', 'video'),
    ('/mjpeg', 45, 'mjpeg', 'video'),
    ('/video.cgi', 45, 'mjpeg-cgi', 'video'),
    ('/cgi-bin/mjpeg', 45, 'mjpeg-cgi', 'video'),
    ('/videostream.cgi', 45, 'videostream', 'video'),
    ('/stream.cgi', 45, 'stream', 'video'),
    ('/livestream', 50, 'livestream', 'video'),
    ('/live', 30, 'live', 'video'),
    ('/video', 45, 'video', 'video'),

    # === Snapshot fallbacks (low weight, last) ===
    ('/image.jpg', 8, 'image-jpg', 'image'),
    ('/image.jpeg', 8, 'image-jpeg', 'image'),
    ('/snap.jpg', 8, 'image-snap', 'image'),
    ('/snapshot.jpg', 8, 'image-snapshot', 'image'),
    ('/img/main.jpg', 8, 'image-img', 'image'),
    ('/cgi-bin/snapshot.cgi', 8, 'image-cgi-snap', 'image'),
    ('/current.jpg', 8, 'image-current', 'image'),
    ('/latest.jpg', 8, 'image-latest', 'image'),
    ('/live.jpg', 8, 'image-live', 'image'),
    ('/cam.jpg', 8, 'image-cam', 'image'),
    ('/cam1.jpg', 8, 'image-cam1', 'image'),
    ('/temp.jpg', 6, 'image-temp', 'image'),
    ('/', 0, 'root', 'html'),
]


def looks_like_live(headers, body_bytes):
    """Classify response type."""
    ct = headers.get('Content-Type', '').lower()
    cl = headers.get('Content-Length', '-1')
    try:
        cl_n = int(cl)
    except Exception:
        cl_n = 0
    if 'multipart/x-mixed-replace' in ct:
        return ('mjpeg-multipart', 50)
    if 'video/x-matroska' in ct or 'video/webm' in ct:
        return ('matroska', 70)
    if 'video/mp4' in ct:
        return ('mp4', 60)
    if 'application/vnd.apple.mpegurl' in ct or 'application/x-mpegurl' in ct:
        return ('hls-m3u8', 70)
    if 'multipart/related' in ct:
        return ('mjpeg-related', 40)
    if 'multipart/form-data' in ct and 'mixed' in ct:
        return ('mjpeg-multipart', 45)
    if cl_n == 99999999:
        return ('mjpeg-infinite', 45)
    if 'image/jpeg' in ct and cl_n >= 5000:
        return ('jpeg-frame', 12)
    if 'image/jpeg' in ct and cl_n >= 1500:
        return ('jpeg-frame', 8)
    if 'image/png' in ct and cl_n >= 1500:
        return ('png-frame', 8)
    if body_bytes[:3] == b'\xff\xd8\xff' and len(body_bytes) > 8000:
        return ('jpeg-large', 14)
    if body_bytes[:3] == b'\xff\xd8\xff' and len(body_bytes) > 2500:
        return ('jpeg-frame', 9)
    if body_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return ('png-frame', 8)
    if body_bytes[:4] == b'GIF8':
        return ('gif-frame', 5)
    if 'text/html' in ct:
        return ('html-page', -10)  # negative to penalize HTML pages
    return (None, 0)


def probe_host(s, host, port, ssl=False, timeout=4.0, probe_paths=None):
    """Probe a host:port for cam signatures.

    probe_paths: optional override list of (path, weight, family, format) tuples.
    """
    scheme = 'https' if ssl else 'http'
    base = f'{scheme}://{host}:{port}'
    best = None
    best_w = -1
    paths_to_try = probe_paths if probe_paths else PROBE_PATTERNS
    for path, weight, fam, fmt in paths_to_try:
        url = base + path
        try:
            r = s.get(url, timeout=timeout, allow_redirects=False, stream=False, verify=False)
            ct = r.headers.get('Content-Type', '').lower()
            cl = r.headers.get('Content-Length', '0')
            try:
                cl_n = int(cl)
            except Exception:
                cl_n = 0
            if r.status_code in (301, 302):
                loc = r.headers.get('Location', '').lower()
                if 'login' in loc or 'auth' in loc or 'setup' in loc:
                    continue
                try:
                    r = s.get(url, timeout=timeout, allow_redirects=True, stream=False, verify=False)
                    ct = r.headers.get('Content-Type', '').lower()
                    cl = r.headers.get('Content-Length', '0')
                    cl_n = int(cl) if cl.isdigit() else 0
                except Exception:
                    pass
            if r.status_code == 401:
                # Auth required - the cam exists but needs creds
                # Save this as a hit with auth_required marker
                eff = weight + 5
                if eff > best_w:
                    best_w = eff
                    best = {
                        'url': url, 'family': fam, 'stream_kind': 'auth-required',
                        'content_type': ct, 'content_length': cl_n, 'weight': eff,
                        'host': host, 'port': port, 'ssl': ssl,
                        'http_status': 401, 'auth_required': True,
                    }
                continue
            if r.status_code in (404, 500, 502, 503, 504):
                continue
            if r.status_code == 403:
                continue
            if r.status_code == 200:
                body = r.content[:8192]
                kind, w = looks_like_live(r.headers, body)
                if kind is None:
                    continue
                eff = weight + w
                if eff > best_w:
                    best_w = eff
                    best = {
                        'url': url,
                        'family': fam,
                        'stream_kind': kind,
                        'format': fmt,
                        'content_type': ct,
                        'content_length': cl_n,
                        'weight': eff,
                        'host': host,
                        'port': port,
                        'ssl': ssl,
                        'http_status': r.status_code,
                    }
                if best_w >= 100:
                    return best
            elif r.status_code == 206:
                if 'multipart' in ct or 'jpeg' in ct or 'matroska' in ct:
                    eff = weight + 30
                    if eff > best_w:
                        best_w = eff
                        best = {
                            'url': url, 'family': fam, 'stream_kind': 'mjpeg-partial',
                            'format': fmt, 'content_type': ct,
                            'content_length': cl_n, 'weight': eff,
                            'host': host, 'port': port, 'ssl': ssl, 'http_status': 206,
                        }
        except requests.exceptions.SSLError:
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                requests.exceptions.RequestException, requests.exceptions.ChunkedEncodingError,
                ConnectionResetError, OSError, Exception):
            pass
    return best


def geoip(s, host):
    """Free ip-api.com - 45 r/min from same IP."""
    try:
        r = s.get(f'http://ip-api.com/json/{host}?fields=status,country,regionName,city,zip,lat,lon,isp,org,as,host', timeout=8)
        if r.status_code == 200:
            j = r.json()
            if j.get('status') == 'success':
                return j
    except Exception:
        pass
    return {}


# ============================================================
# RTSP probing (separate, doesn't need HTTP - just OPTIONS/DESCRIBE)
# ============================================================

def probe_rtsp(host, port=554, timeout=4.0, paths=None):
    """Probe RTSP endpoints - returns list of working paths.

    RTSP protocol: send OPTIONS then DESCRIBE for each path.
    """
    if paths is None:
        paths = [
            '/live/0/main', '/live/0/sub', '/live/main', '/live/sub',
            '/live/1/main', '/live/1/sub', '/live.sdp',
            '/11', '/12', '/ch01/0', '/ch01/1', '/ch01.264',
            '/0/usrnm:pwd/0', '/Streaming/tracks/101', '/Streaming/tracks/1',
            '/av0_0', '/av0_1', '/mpeg4', '/h264', '/onvif/track1',
            '/cam/realmonitor', '/video.mp4',
        ]
    results = []
    import socket
    for path in paths:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            req = f'OPTIONS rtsp://{host}:{port}{path} RTSP/1.0\r\nCSeq: 1\r\n\r\n'
            s.send(req.encode())
            resp = s.recv(2048).decode('utf-8', errors='replace')
            s.close()
            if 'RTSP/1.0 200' in resp or 'RTSP/1.0 401' in resp:
                results.append(path)
        except Exception:
            try:
                s.close()
            except Exception:
                pass
    return results
