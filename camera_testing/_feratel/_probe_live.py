import re, json, os, sys, time, ssl, urllib.request, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.join(ROOT, 'cams_final.json')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36',
      'Accept': 'text/html', 'Accept-Language': 'en-US,en;q=0.9'}
CTX = ssl.create_default_context()

def req(url, headers=None, timeout=25):
    r = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(r, timeout=timeout, context=CTX) as resp:
        return resp.read(), dict(resp.headers), resp.status

def probe(camid):
    out = {'camid': camid, 'live_url': None, 'live_status': 'none', 'error': None}
    try:
        body, _, _ = req(f'https://webtvfc.feratel.com/webtv/?cam={camid}&t=1&lg=en&design=v5')
        html = body.decode('utf-8', 'replace')
        m = re.search(r'property="og:video" content="([^"]+)"', html)
        if not m:
            # og:video absent -> maybe t=0 only (image cam)
            m2 = re.search(r'property="og:image" content="([^"]+)"', html)
            out['webtv_og_image'] = m2.group(1) if m2 else None
            out['error'] = 'no-og-video'
            return out
        url = m.group(1)
        out['live_url'] = url
        body2, hdr, st = req(url, {'Range': 'bytes=0-0'}, timeout=20)
        out['http_status'] = st
        cr = hdr.get('Content-Range', '')
        out['frag_size'] = int(cr.rsplit('/', 1)[1]) if '/' in cr else None
        et = (hdr.get('ETag') or '').strip('"')
        out['etag'] = et
        if et and et.split('_')[0].isdigit():
            ts = int(et.split('_')[0]) / 1000.0
            now = time.time()
            out['frag_mtime'] = datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%SZ')
            out['frag_age_s'] = round(now - ts)
        out['last_modified'] = hdr.get('Last-Modified')
        out['live_status'] = 'live' if st == 206 else f'http-{st}'
        age = out.get('frag_age_s')
        if age is not None:
            if age > 86400:
                out['live_status'] = 'stale-day'
            elif age > 600:
                out['live_status'] = 'stale-10m'
    except urllib.error.HTTPError as e:
        out['error'] = f'HTTP {e.code}'
        out['http_status'] = e.code
    except Exception as e:
        out['error'] = repr(e)[:150]
    return out

def main():
    recs = json.load(open(FINAL, encoding='utf-8'))
    outp = os.path.join(ROOT, 'live_probes.jsonl')
    done = set()
    if os.path.exists(outp):
        for l in open(outp, encoding='utf-8'):
            try:
                done.add(json.loads(l)['camid'])
            except Exception:
                pass
    todo = [r for r in recs if str(r['url_camid']) not in done]
    print(f'{len(recs)} cams, {len(done)} probed, {len(todo)} todo', flush=True)
    n = collections_ok = 0
    with open(outp, 'a', encoding='utf-8') as out, ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(probe, str(r['url_camid'])): r for r in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            r = futs[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {'camid': str(r['url_camid']), 'error': repr(e)[:150], 'live_status': 'error'}
            out.write(json.dumps(res, ensure_ascii=False) + '\n')
            n += 1
            if res.get('live_status') == 'live':
                collections_ok += 1
            if i % 100 == 0:
                out.flush()
                print(f'{i}/{len(todo)} live={collections_ok}', flush=True)
    print(f'DONE {n} probed, live={collections_ok}', flush=True)

if __name__ == '__main__':
    main()
