import re, json, html, sys, os, time, ssl, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
URLS = os.path.join(ROOT, 'cam_urls.txt')
OUT = os.path.join(ROOT, 'cams2.jsonl')
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

def parse(page_url, raw):
    m = re.search(r'-(\d+)$', page_url)
    url_camid = m.group(1) if m else None
    rec = {'page': page_url, 'url_camid': url_camid, 'errors': []}

    for k, pat in (
        ('og_title', r'<meta property="og:title" content="([^"]*)"'),
        ('og_image', r'<meta property="og:image" content="([^"]*)"'),
        ('description', r'<meta name="description" content="([^"]*)"'),
    ):
        mm = re.search(pat, raw)
        if mm:
            rec[k] = html.unescape(mm.group(1))

    islands = []
    for pm in re.finditer(r'<astro-island[^>]*?props="([^"]+)"', raw):
        try:
            islands.append(json.loads(html.unescape(pm.group(1))))
        except Exception:
            islands.append(None)

    # main player island: cam = {id: uuid}; island w/ cam-id attr
    main_uuid = None
    camid_attr = None
    for obj in islands:
        if not obj:
            continue
        cam = obj.get('cam')
        if isinstance(cam, list) and len(cam) == 2 and isinstance(cam[1], dict) and set(cam[1].keys()) == {'id'}:
            main_uuid = deval(cam[1].get('id'))
        if 'cam-id' in obj:
            camid_attr = str(obj.get('cam-id'))

    # full cam objects from any island
    full = []
    for obj in islands:
        if not obj:
            continue
        cam = obj.get('cam')
        if not cam:
            continue
        try:
            d = deval(cam)
        except Exception as e:
            rec['errors'].append(f'deval:{e}')
            continue
        if isinstance(d, dict) and (d.get('camId') or d.get('id')):
            full.append(d)

    main = None
    for c in full:
        if str(c.get('camId')) == str(url_camid):
            main = c
            break
    if main is None and main_uuid:
        for c in full:
            if c.get('id') == main_uuid:
                main = c
                break
    if main is None and camid_attr:
        for c in full:
            if str(c.get('camId')) == camid_attr:
                main = c
                break
    if main is None:
        for c in full:
            ogm = re.search(r'picture/\d+/(\d+)\.jpeg', c.get('poster') or '')
            if ogm and ogm.group(1) == str(url_camid):
                main = c
                break

    rec['main_uuid'] = main_uuid
    rec['camid_attr'] = camid_attr
    if main is None:
        rec['errors'].append('no-main-object')
        # synthesize minimal from meta
        main = {'camId': url_camid, 'name': (rec.get('og_title') or '').replace('Webcams in ', ''),
                'id': main_uuid}
        ogm = re.search(r'picture/(\d+)/(\d+)\.jpeg', rec.get('og_image') or '')
        if ogm:
            main['poster'] = rec.get('og_image')
    rec['cam'] = main
    rec['main_from_slider'] = bool(main and 'no-main-object' not in rec['errors'])

    seen = {str(main.get('camId'))}
    rel = []
    for c in full:
        cid = str(c.get('camId') or '')
        if cid and cid not in seen:
            seen.add(cid)
            rel.append(c)
    rec['related'] = rel

    lds = []
    for jm in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S):
        try:
            lds.append(json.loads(jm.group(1)))
        except Exception:
            pass
    for ld in lds:
        t = ld.get('@type')
        if t == 'VideoObject':
            rec['video_object'] = {k: ld.get(k) for k in
                                   ('name', 'description', 'contentUrl', 'embedUrl',
                                    'thumbnailUrl', 'uploadDate', 'duration')}
        elif t == 'Place':
            rec['place'] = {k: ld.get(k) for k in ('name', 'geo')}

    parts = page_url.split('/webcams/', 1)
    if len(parts) == 2:
        segs = parts[1].split('/')
        rec['path'] = {'country': segs[0] if len(segs) > 0 else None,
                       'region': segs[1] if len(segs) > 1 else None,
                       'slug': segs[2] if len(segs) > 2 else None}
    return rec

def main():
    urls = [u.strip() for u in open(URLS, encoding='utf-8') if u.strip()]
    n_ok = n_fail = 0

    def work(u):
        return u, parse(u, fetch(u))

    with open(OUT, 'w', encoding='utf-8') as out, ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(work, u): u for u in urls}
        for i, fut in enumerate(as_completed(futs), 1):
            u = futs[fut]
            try:
                _, rec = fut.result()
                out.write(json.dumps(rec, ensure_ascii=False) + '\n')
                n_ok += 1
            except Exception as e:
                out.write(json.dumps({'page': u, 'errors': [repr(e)]}, ensure_ascii=False) + '\n')
                n_fail += 1
            if i % 100 == 0:
                out.flush()
                print(f'{i}/{len(urls)} ok={n_ok} fail={n_fail}', flush=True)
    print(f'DONE ok={n_ok} fail={n_fail}', flush=True)

if __name__ == '__main__':
    main()
