"""Advanced bypass: Nmap-style scan + curl variants + SOCKS attempts.

Try what curl --resolve and other tools can do.
"""
import socket
import ssl
import urllib.request
import urllib.error
import time

host = '212.25.48.117'
port = 8080


def make_request(url, headers, body=None, timeout=8):
    """Make HTTP/HTTPS request with specified headers."""
    try:
        if body:
            req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        else:
            req = urllib.request.Request(url, headers=headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return (r.status, dict(r.headers), r.read()[:500])
    except urllib.error.HTTPError as e:
        return (e.code, dict(e.headers) if e.headers else {}, b'')
    except Exception as e:
        return (None, {}, str(e).encode()[:200])


# Test using User-Agents that Ruse city cam services use
ua_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'curl/8.5.0',
    'wget/1.21.4',
    'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)',
    'masscan/1.0',
    'Nmap NSE',
    'Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)',
    'Mediapartners-Google',
    'LBtron/1.0',
    'Apache-HttpClient/4.5.14',
    'python-requests/2.31.0',
    'python-urllib/3.10',
    'Go-http-client/1.1',
    'CamCheck/1.0',
    'Elvideo/2.5',
    'VLC/3.0.18',
    'ffmpeg/4.4',
    'libcurl/7.88.1',
]

print(f'=== Testing {host}:{port} with various UAs and headers ===')

for ua in ua_list:
    headers = {
        'User-Agent': ua,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5,bg;q=0.3',
        'Connection': 'keep-alive',
        'X-Forwarded-For': '85.130.0.1',
        'Via': '1.1 85.130.0.1',
    }
    for path in ['/', '/axis-cgi/mjpg/video.cgi', '/mjpg/video.mjpg']:
        url = f'http://{host}:{port}{path}'
        status, hdrs, body = make_request(url, headers, timeout=5)
        if status not in [None, 'time', 'timeout']:
            print(f'  UA={ua[:20]:20} Path={path:25} Status={status} Body={body[:100]}')
            if status == 200 and not b'html' in body:
                break

# Try HTTPS too
print('\n=== Try HTTPS ===')
for path in ['/', '/axis-cgi/mjpg/video.cgi']:
    url = f'https://{host}:8443{path}'
    status, hdrs, body = make_request(url, {'User-Agent': 'Mozilla/5.0'}, timeout=5)
    print(f'  HTTPS {path}: status={status}')

# Try direct TCP and send raw requests
print('\n=== Direct TCP with various flags ===')
for send_data in [
    b'\r\n',  # keepalive
    b'GET / HTTP/0.9\r\n\r\n',  # old HTTP
    b'GET / HTTP/1.1\r\nHost: cam.ruse.bg\r\n\r\n',  # different host
    b'OPTIONS / HTTP/1.1\r\nHost: ' + host.encode() + b'\r\n\r\n',
    b'CONNECT ' + host.encode() + b':80 HTTP/1.1\r\nHost: ' + host.encode() + b'\r\n\r\n',  # CONNECT
]:
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.send(send_data)
        sock.settimeout(3)
        data = b''
        try:
            while len(data) < 4096:
                d = sock.recv(1024)
                if not d: break
                data += d
        except: pass
        sock.close()
        if data:
            preview = data[:150].decode('utf-8', errors='replace').replace('\n', '\\n')
            print(f'  Sent: {send_data[:40]!r} Response: {preview}')
    except Exception as e:
        print(f'  Sent: {send_data[:30]!r}: {str(e)[:60]}')
