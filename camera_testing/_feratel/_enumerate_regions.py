import re, json, html, os, sys, time, ssl, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
SM = os.path.join(os.environ.get('TEMP', ''), 'feratel_sitemap0.xml')
OUT = os.path.join(ROOT, 'region_cams.jsonl')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'en-US,en;q=0.9'}
CTX = ssl.create_default_context()

def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last

def deval(o):
    if isinstance(o, list):
        if len(o) == 2 and isinstance(o[0], int):
            if o[0] == 0:
                return deval(o[1])
            if o[0] == 1:
                return [deval(x) for x in o[1]]
        return [deval(x) for x in o]
    if isinstance(o, dict):
        return {k: deval(v) for k, v in o.items()}
    return o

def cam_objects(raw):
    out = []
    for pm in re.finditer(r'<astro-island[^>]*?props="([^"]+)"', raw):
        try:
            obj = json.loads(html.unescape(pm.group(1)))
        except Exception:
            continue
        cam = obj.get('cam')
        if not cam:
            continue
        try:
            d = deval(cam)
        except Exception:
            continue
        if isinstance(d, dict) and d.get('camId') and (d.get('geo') or {}).get('latitude'):
            out.append(d)
    return out

def main():
    xml = open(SM, encoding='utf-8', errors='replace').read()
    urls = re.findall(r'<loc>(https://www\.feratel\.com/webcams/[^<]+)</loc>', xml)
    # index pages: path after webcams/ has 1 or 2 segments and last segment not -<digits>
    idx = []
    for u in urls:
        path = u.split('/webcams/', 1)[1].strip('/')
        segs = path.split('/')
        if len(segs) in (1, 2) and not re.search(r'-\d+$', segs[-1]):
            idx.append(u)
    idx = sorted(set(idx))
    print(f'{len(urls)} sitemap urls, {len(idx)} index pages', flush=True)

    def work(u):
        return u, cam_objects(fetch(u))

    n_ok = n_fail = 0
    with open(OUT, 'w', encoding='utf-8') as out, ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(work, u): u for u in idx}
        for i, fut in enumerate(as_completed(futs), 1):
            u = futs[fut]
            try:
                _, cams = fut.result()
                for c in cams:
                    out.write(json.dumps({'src': u, 'cam': c}, ensure_ascii=False) + '\n')
                n_ok += 1
            except Exception as e:
                out.write(json.dumps({'src': u, 'error': repr(e)}) + '\n')
                n_fail += 1
            if i % 50 == 0:
                out.flush()
                print(f'{i}/{len(idx)} ok={n_ok} fail={n_fail}', flush=True)
    print(f'DONE ok={n_ok} fail={n_fail}', flush=True)

if __name__ == '__main__':
    main()
