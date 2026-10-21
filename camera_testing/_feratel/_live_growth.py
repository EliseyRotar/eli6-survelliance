import re, urllib.request, ssl, time, sys, json

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0'}
CTX = ssl.create_default_context()

def get(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
        return r.read(), dict(r.headers), r.status

def og_video(cam):
    body, _, _ = get(f'https://webtvfc.feratel.com/webtv/?cam={cam}&t=1&lg=en&design=v5')
    m = re.search(rb'property="og:video" content="([^"]+)"', body)
    return m.group(1).decode() if m else None

def probe(url):
    out = {}
    try:
        body, hdr, st = get(url, {'Range': 'bytes=0-0'})
        out['status'] = st
        out['content_range'] = hdr.get('Content-Range')
        out['etag'] = hdr.get('ETag')
        out['last_modified'] = hdr.get('Last-Modified')
        out['accept_ranges'] = hdr.get('Accept-Ranges')
        out['content_length'] = hdr.get('Content-Length')
        out['server'] = hdr.get('Server')
        out['set_cookie'] = hdr.get('Set-Cookie')
        # full HEAD-ish: fetch last bytes to see growth tail
        if hdr.get('Content-Range'):
            total = int(hdr['Content-Range'].rsplit('/', 1)[1])
            body2, hdr2, st2 = get(url, {'Range': f'bytes={max(0,total-4096)}-{total-1}'})
            out['tail_status'] = st2
            out['tail_etag'] = hdr2.get('ETag')
            out['tail_len'] = hdr2.get('Content-Length')
    except Exception as e:
        out['error'] = repr(e)
    return out

for cam in sys.argv[1:] or ['8000004']:
    print(f'=== cam {cam} ===', flush=True)
    for roundno in (0, 1):
        v = og_video(cam)
        print(f'round {roundno} og:video: {v}', flush=True)
        if v:
            p = probe(v)
            print(f'round {roundno} probe: {json.dumps(p, indent=1)}', flush=True)
        if roundno == 0:
            time.sleep(75)
