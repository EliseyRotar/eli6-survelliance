"""Reverse IP and /24 scan to find related Ruse cams.

Since 212.25.48.117 is geofenced, find the cam's other access points:
1. Scan /24 subnet (212.25.48.0/24) for any open ports
2. Check if cam is also accessible via different hostname
3. Find the cam's geolocation and operator via IP geolocation
4. Check if there's a public-facing mirror
"""
import socket
import csv
import json
import urllib.request
import urllib.error
import time

host = '212.25.48.117'


def probe_port(ip, port, timeout=3):
    """Probe one (ip, port)."""
    try:
        sock = socket.create_connection((ip, port), timeout=timeout)
        # Send small probe
        sock.send(b'GET / HTTP/1.0\r\nHost: ' + ip.encode() + b'\r\n\r\n')
        sock.settimeout(2)
        data = b''
        try:
            while len(data) < 2048:
                d = sock.recv(1024)
                if not d: break
                data += d
        except: pass
        sock.close()
        if b'HTTP' in data[:200] or b'RTSP' in data[:200]:
            # Parse header
            first_line = data.split(b'\r\n')[0].decode('utf-8', errors='replace')
            server = ''
            ct = ''
            for line in data.split(b'\r\n')[:20]:
                if line.lower().startswith(b'server:'):
                    server = line[7:].strip().decode('utf-8', errors='replace')
                elif line.lower().startswith(b'content-type:'):
                    ct = line[12:].strip().decode('utf-8', errors='replace')
            return {'port': port, 'status_line': first_line, 'server': server, 'content_type': ct}
    except (socket.timeout, ConnectionRefusedError, OSError):
        return None
    except Exception:
        return None
    return {'port': port, 'status': 'unreachable'}


def scan_subnet(prefix='212.25.48', count=20):
    """Scan IPs in the /24 subnet near the cam."""
    print(f'\n=== Scanning {prefix}.0/24 (first {count} IPs) ===')
    found = []
    for i in range(1, count + 1):
        ip = f'{prefix}.{i}'
        if ip == host:
            continue
        for port in [80, 443, 554, 8080, 8081, 8000, 8443, 7070, 8554]:
            r = probe_port(ip, port, timeout=4)
            if r and 'status_line' in r and ('200' in r['status_line'] or '401' in r['status_line'] or '302' in r['status_line']):
                found.append({'ip': ip, 'port': port, **r})
                print(f'  {ip}:{port} - {r["status_line"][:80]} server={r.get("server", "")[:30]}')
    print(f'\n  Total found: {len(found)}')
    return found


def find_cam_geolocation():
    """Find IP geolocation for 212.25.48.117."""
    print(f'\n=== Geolocation for {host} ===')
    sources = [
        'https://ipinfo.io/' + host + '/json',
        'https://ipapi.co/' + host + '/json/',
        f'https://api.allorigins.win/get?url=https://ipapi.co/{host}/json/',
        'http://ip-api.com/json/' + host,
    ]
    for url in sources:
        try:
            ctx = ssl.create_default_context() if url.startswith('https') else None
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            ctx_arg = {'context': ctx} if ctx else {}
            with urllib.request.urlopen(req, timeout=10, **ctx_arg) as r:
                data = r.read()
                print(f'  {url[-50:]}: {data[:300]}')
        except Exception as e:
            emsg = str(e)[:60]
            print(f'  {url[-50:]}: {emsg}')


def find_ruse_cam_cameras():
    """Search for Ruse cams on 212.25.x.x range (Ruse providers)."""
    print(f'\n=== Subnet scan for other Ruse cams ===')
    # These are Ruse cable operator subnets
    ruse_subnets = [
        '212.25.48',  # where cam is
        '212.25.49',
        '212.25.50',
        '212.25.51',
        '212.25.52',
    ]
    all_found = {}
    for sub in ruse_subnets:
        for i in range(1, 30):
            ip = f'{sub}.{i}'
            for port in [80, 554, 8080]:
                r = probe_port(ip, port, timeout=3)
                if r and 'status_line' in r and '200' in r.get('status_line', ''):
                    if 'cam' in r.get('server', '').lower() or 'axis' in r.get('server', '').lower() or 'mjpg' in r.get('content_type', '').lower():
                        all_found.setdefault(ip, []).append({port: r})
    if all_found:
        print(f'  Found {len(all_found)} cam-like IPs:')
        for ip, ports in all_found.items():
            print(f'    {ip}: {ports[:1]}')
    else:
        print(f'  No cam-like servers found in Ruse range')


def reverse_dns():
    """Try reverse DNS."""
    print(f'\n=== Reverse DNS for {host} ===')
    try:
        name = socket.gethostbyaddr(host)
        print(f'  {host} -> {name}')
    except Exception as e:
        print(f'  No reverse DNS: {e}')


if __name__ == '__main__':
    import ssl
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    print('=== Ruse Cam Bypass Toolkit ===')
    reverse_dns()
    find_cam_geolocation()
    scan_subnet(count=20)
    find_ruse_cam_cameras()
