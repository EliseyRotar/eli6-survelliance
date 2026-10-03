"""fl511 helper: build a working HLS URL for a given cam_idx (dashboard row).

Session 21 architecture (replaces session 20's host-lookup approach):

1. fl511.com has 4,555 cams total, discoverable via:
   `https://fl511.com/List/GetData/Cameras?query=...&search=<name>` (paginated, 100/page)
   Returns: id (int), images[0].videoUrl (string, with host), sourceId, location, etc.

2. For 4,014/4,555 cams, videoUrl is populated like:
   `https://dis-se9.divas.cloud:8200/chan-1471_h/index.m3u8`
   The `chan-N` is NOT the sourceId returned by fl511 GetVideoUrl — it's a
   separate Divas identifier. We just use videoUrl as-is.

3. To get the LIVE HLS stream:
   - Replace `index.m3u8` with `xflow.m3u8` in the videoUrl
   - Append `?token=...` from divas POST
   - Result: `https://dis-se9.divas.cloud:8200/chan-1471_h/xflow.m3u8?token=...`
   - This returns a media playlist with .mp4 (or .ts) segments — REAL video.

4. 541 cams have EMPTY videoUrl in /List/GetData. We try 26 servers (se1-se26)
   with the sourceId from /Camera/GetVideoUrl. If none return 200, cam is defunct.

5. The fl511.com endpoint flow:
   a) GET /cctv → get __RequestVerificationToken + session cookie
   b) GET /List/GetData/Cameras?query=...&search=<name> → cam_id, videoUrl, sourceId
      (can be done without CSRF if we just want the list, but CSRF works too)
   c) GET /Camera/GetVideoUrl?imageId=N → {token, sourceId, systemSourceId}
   d) POST https://divas.cloud/VDS-API/SecureTokenUri/GetSecureTokenUriBySourceId
      body: {token, sourceId, systemSourceId}
      → "?token=ABC..." (literally that string with leading ")

This module provides a single high-level function:
    get_live_hls_for_cam_id(cam_id, session) -> {xflow_url, video_url} or None
"""
import csv
import json
import os
import re
import time
import urllib.request
import urllib.error
import ssl
import http.cookiejar
import urllib.parse

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

WORK_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = f'{WORK_DIR}\\controllable_Webcams.csv'
TOKENS_PATH = f'{WORK_DIR}\\data\\fl511_divas_full_tokens.json'
ALL_CAMS_PATH = f'{WORK_DIR}\\data\\fl511_all_cams.json'

# Cache of fl511 /List/GetData (built once per process)
_ALL_CAMS = None
_CAMS_BY_ID = None


def _load_all_cams():
    """Load fl511_all_cams.json (full scrape of 4,555 cams from /List/GetData)."""
    global _ALL_CAMS, _CAMS_BY_ID
    if _ALL_CAMS is not None:
        return _ALL_CAMS
    if not os.path.exists(ALL_CAMS_PATH):
        return None
    with open(ALL_CAMS_PATH, encoding='utf-8') as f:
        cams = json.load(f)
    _ALL_CAMS = cams
    _CAMS_BY_ID = {c['id']: c for c in cams}
    return _ALL_CAMS


def get_cam_from_cache(image_id):
    """Return cached cam dict (with videoUrl, sourceId, etc.) for image_id, or None."""
    _load_all_cams()
    return _CAMS_BY_ID.get(image_id)


def get_fl511_session():
    """Get fresh fl511 session cookies + __RequestVerificationToken."""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=ctx),
    )
    req = urllib.request.Request('https://fl511.com/cctv', headers={'User-Agent': 'Mozilla/5.0'})
    with opener.open(req, timeout=15) as r:
        html = r.read().decode('utf-8', errors='replace')
    m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html)
    if not m:
        return None, None
    token = m.group(1)
    cookie_str = '; '.join(f'{c.name}={c.value}' for c in cj)
    return cookie_str, token


def get_divas_token(fl_token_data, session):
    """Call divas.cloud with the fl511 token/sourceId/systemSourceId to get a divas session token.

    fl_token_data: dict with 'token', 'sourceId', 'systemSourceId' (from fl511 GetVideoUrl)
    session: dict with 'cookies' and 'token' (fl511)
    Returns: session_token string like '?token=ABC...' (with leading ?), or None.
    """
    try:
        req = urllib.request.Request(
            'https://divas.cloud/VDS-API/SecureTokenUri/GetSecureTokenUriBySourceId',
            data=json.dumps(fl_token_data).encode(),
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': '*/*',
                'Origin': 'https://fl511.com',
                'Referer': 'https://fl511.com/',
                'Content-Type': 'application/json',
                '__RequestVerificationToken': session['token'],
                'Cookie': session['cookies'],
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            raw = r.read().decode('utf-8', errors='replace').strip().strip('"')
        if not raw.startswith('?'):
            raw = '?' + raw
        return raw
    except Exception:
        return None


def get_fl511_token(image_id, session):
    """Hit fl511 GetVideoUrl for a specific image_id. Returns dict or None."""
    try:
        ts = int(time.time() * 1000)
        url = f'https://fl511.com/Camera/GetVideoUrl?imageId={image_id}&_={ts}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            '__RequestVerificationToken': session['token'],
            'Cookie': session['cookies'],
            'Referer': 'https://fl511.com/cctv',
            'Origin': 'https://fl511.com',
        })
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            data = json.loads(r.read().decode('utf-8', errors='replace'))
        if 'token' in data and 'sourceId' in data:
            return data
    except Exception:
        pass
    return None


def build_xflow_url(video_url_base, divas_token):
    """Given the videoUrl (with index.m3u8) and divas token (?token=...),
    return the LIVE xflow.m3u8 URL.

    Example:
      video_url_base = 'https://dis-se9.divas.cloud:8200/chan-1471_h/index.m3u8'
      divas_token = '?token=abc...'
      -> 'https://dis-se9.divas.cloud:8200/chan-1471_h/xflow.m3u8?token=abc...'
    """
    return video_url_base.replace('index.m3u8', 'xflow.m3u8') + divas_token


def probe_xflow(url, timeout=5):
    """Test if a xflow.m3u8 URL works (returns a valid media playlist)."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Origin': 'https://fl511.com',
            'Referer': 'https://fl511.com/',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            ct = r.headers.get('Content-Type', '')
            if r.status == 200 and 'mpegurl' in ct:
                body = r.read().decode('utf-8', errors='replace')
                if '#EXTM3U' in body:
                    return True
    except Exception:
        pass
    return False


def get_live_hls_for_image_id(image_id, session, brute_force=True):
    """Get a working HLS xflow URL for an image_id.

    Returns (xflow_url, video_url_base) or None if cam is defunct.

    The video_url_base is the index.m3u8 URL (with NO token) — useful for caching.
    """
    cam = get_cam_from_cache(image_id)
    video_url = (cam or {}).get('images', [{}])[0].get('videoUrl', '') if cam else ''

    if video_url:
        # Fast path: videoUrl exists, just need a divas token
        fl_data = get_fl511_token(image_id, session)
        if not fl_data:
            return None
        divas_token = get_divas_token(fl_data, session)
        if not divas_token:
            return None
        xflow = build_xflow_url(video_url, divas_token)
        if probe_xflow(xflow):
            return xflow, video_url
        return None

    if not brute_force:
        return None

    # Slow path: videoUrl empty, try 26 servers with sourceId
    fl_data = get_fl511_token(image_id, session)
    if not fl_data:
        return None
    divas_token = get_divas_token(fl_data, session)
    if not divas_token:
        return None
    source_id = fl_data.get('sourceId', '')
    for n in range(1, 27):
        test_url = build_xflow_url(
            f'https://dis-se{n}.divas.cloud:8200/chan-{source_id}_h/index.m3u8',
            divas_token,
        )
        if probe_xflow(test_url, timeout=3):
            video_url = f'https://dis-se{n}.divas.cloud:8200/chan-{source_id}_h/index.m3u8'
            return test_url, video_url
    return None


# Backwards compat: keep old function signatures for hls_proxy.py
def lookup_host_for_chan(chan_n):
    """Look up which dis-se{N} server hosts chan_n. Returns server_n or None.
    Used by old code; not the primary lookup anymore.
    """
    _load_all_cams()
    for c in _ALL_CAMS or []:
        v = c.get('images', [{}])[0].get('videoUrl', '')
        m = re.search(r'chan-' + re.escape(str(chan_n)) + r'_h', v)
        if m:
            host_m = re.search(r'dis-se(\d+)', v)
            if host_m:
                return int(host_m.group(1))
    return None


def build_host_for_chan(chan_n):
    """Return host string or default fallback. Used by old code."""
    n = lookup_host_for_chan(chan_n)
    if n:
        return f'https://dis-se{n}.divas.cloud:8200'
    return 'https://dis-se1.divas.cloud:8200'


def get_divas_token_for_cam(cam_id, session, prefer_host=None):
    """Backwards compat: returns (xflow_url, divas_token, source_id, sys_source).

    live_url is the WORKING xflow.m3u8 URL (with token), suitable for direct playback.
    cam_id may be None — in that case, we try to find via host brute force.
    """
    try:
        # Fast path: cam is in our cache with known videoUrl
        cam = get_cam_from_cache(int(cam_id)) if (cam_id is not None and str(cam_id).isdigit()) else None
        if cam:
            v = cam.get('images', [{}])[0].get('videoUrl', '')
            if v:
                fl_data = get_fl511_token(cam_id, session)
                if not fl_data:
                    return None, None, None, None
                divas_token = get_divas_token(fl_data, session)
                if not divas_token:
                    return None, None, None, None
                xflow = build_xflow_url(v, divas_token)
                if probe_xflow(xflow, timeout=4):
                    return xflow, divas_token, fl_data.get('sourceId', ''), fl_data.get('systemSourceId', '')

        # Slow path: cam_id is None or not in cache, brute force
        # Need a cam_id to call get_fl511_token. Skip the brute if no cam_id.
        if not (cam_id is not None and str(cam_id).isdigit()):
            return None, None, None, None
        fl_data = get_fl511_token(cam_id, session)
        if not fl_data:
            return None, None, None, None
        divas_token = get_divas_token(fl_data, session)
        if not divas_token:
            return None, None, None, None
        source_id = fl_data['sourceId']
        sys_source = fl_data.get('systemSourceId', '')

        # Try prefer_host first, then brute force
        hosts_to_try = []
        if prefer_host:
            hosts_to_try.append(prefer_host)
        if cam:
            v = cam.get('images', [{}])[0].get('videoUrl', '')
            if v:
                host_m = re.match(r'(https?://dis-se\d+\.divas\.cloud:8200)', v)
                if host_m:
                    hosts_to_try.insert(0, host_m.group(1))
        for n in range(1, 27):
            h = f'https://dis-se{n}.divas.cloud:8200'
            if h not in hosts_to_try:
                hosts_to_try.append(h)

        for host in hosts_to_try:
            video_url = f'{host}/chan-{source_id}_h/index.m3u8'
            xflow = build_xflow_url(video_url, divas_token)
            if probe_xflow(xflow, timeout=3):
                return xflow, divas_token, source_id, sys_source
        return None, None, None, None
    except Exception:
        return None, None, None, None
