"""Mass-scan pre-check: identify cam vendors on open ports before full probe.

Sniffs root URL response (server header, HTML title, body) for cam vendors:
- AXIS (Server: AXIS* or 'AXIS' in HTML)
- Hikvision (Server: App-webs/, realm="Hikvision")
- Dahua (Server: Dahua, /RPC2)
- WebcamXP/WebcamXP 5 (Server: WebcamXP*, /cam_1.cgi in HTML)
- HiSilicon Hi3510/Hi3518 (Server: HiSilicon)
- Reolink (Server: Reolink)
- TP-Link Tapo (Server: Tapo)
- HIPcam (Server: HIPcam)
- Mobotix (Server: MxPEG)
- ONVIF (XML namespace 'http://www.onvif.org')

Returns True if cam-like, prompting full probe.
"""
import requests


CAM_SERVER_HEADERS = {
    'axis', 'hikvision', 'dahua', 'webcamxp', 'webcamxp 5', 'hisilicon',
    'reolink', 'tapo', 'hipcam', 'mobotix', 'mxpeg', 'ubnt', 'unifi video',
    'blue iris', 'ivideon', 'geovision', 'avigilon', 'synology', 'qnap',
    'annke', 'ezviz', 'sannce', 'lorex', 'swann', 'annke', 'bosch',
    'panasonic', 'sony', 'canon', 'vivotek', 'arecont', 'avigilon',
    'avigilon', 'avigilon', 'truenas', 'foscam', 'wansview', 'wanscam',
    'sricam', 'tenvis', 'easycam', 'trendnet', 'dlink', 'tp-link',
    'y-cam', 'y cam', 'yicam', 'airlive', 'edimax', 'lilin',
    'grandstream', 'doorbell', 'ring', 'arlo', 'nest', 'wyze',
    'icsee', 'nvr', 'dvr', 'ipc', 'vms',
}

CAM_REALM_PATTERNS = ['ipcamera', 'webcam', 'ipcam', 'camserver', 'ip cam']


def sniffer(s, host, port, ssl=False, timeout=4.0):
    """Quick probe of root URL to check if it's a cam server.
    Returns True if looks like cam; False otherwise.
    """
    scheme = 'https' if ssl else 'http'
    base = f'{scheme}://{host}:{port}'
    try:
        r = s.get(base, timeout=timeout, allow_redirects=True, verify=False, stream=True)
        if r.status_code >= 400:
            return False, None
        server = r.headers.get('Server', '').lower()
        realm = r.headers.get('WWW-Authenticate', '').lower()
        content_type = r.headers.get('Content-Type', '').lower()
        # Check server header
        for vendor in CAM_SERVER_HEADERS:
            if vendor in server:
                return True, f'server-header:{vendor}'
        # Check realm
        if 'realm=' in realm:
            for pat in CAM_REALM_PATTERNS:
                if pat in realm:
                    return True, f'realm:{pat}'
        # Read first 32KB of body for HTML
        if 'text/html' in content_type or 'text/plain' in content_type:
            try:
                body = r.raw.read(32768, decode_content=True).decode('utf-8', errors='replace')
                body_low = body.lower()
                for vendor in ['axis', 'hikvision', 'dahua', 'webcamxp', 'hisilicon', 'hipcam', 'reolink', 'mobotix']:
                    if vendor in body_low:
                        return True, f'body:{vendor}'
                # Hikvision "faf10279fddf6796cd7795d0" realm pattern
                if 'faf' in body_low and 'realm' in body_low:
                    return True, 'body:hik-realm'
            except Exception:
                pass
        return False, None
    except Exception:
        return False, None
