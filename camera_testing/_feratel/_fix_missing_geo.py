import re, json, os, sys, time, ssl, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.join(ROOT, 'cams_final.json')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36',
      'Accept': 'text/html', 'Accept-Language': 'en-US,en;q=0.9'}
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

def ld_items(raw):
    for jm in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S):
        try:
            ld = json.loads(jm.group(1))
        except Exception:
            continue
        yield ld
        for sub in ld.get('@graph', []) or []:
            yield sub

def place_geo(raw):
    for ld in ld_items(raw):
        if ld.get('@type') == 'Place':
            g = ld.get('geo') or {}
            if g.get('latitude') is not None:
                return {'lat': g['latitude'], 'lon': g.get('longitude'), 'place': ld.get('name')}
    return None

def main():
    recs = json.load(open(FINAL, encoding='utf-8'))
    todo = [r for r in recs if r['lat'] is None]
    print(f'{len(todo)} pages to fix', flush=True)

    def work(r):
        return r['page'], place_geo(fetch(r['page']))

    by_page = {}
    n_ok = n_fail = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(work, r): r for r in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            r = futs[fut]
            try:
                page, g = fut.result()
                if g:
                    by_page[page] = g
                    n_ok += 1
                else:
                    n_fail += 1
            except Exception as e:
                n_fail += 1
                print('ERR', r['page'], repr(e)[:100], flush=True)
            if i % 40 == 0:
                print(f'{i}/{len(todo)} geo_found={n_ok}', flush=True)
    print(f'place geo found for {n_ok}, none/fail {n_fail}', flush=True)

    for r in recs:
        if r['lat'] is None and r['page'] in by_page:
            g = by_page[r['page']]
            r['lat'], r['lon'] = g['lat'], g['lon']
            r['geo_source'] = 'jsonld-place'
            r['place_name'] = g['place']
    json.dump(recs, open(FINAL, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    with_geo = sum(1 for r in recs if r['lat'] is not None)
    print(f'now with geo: {with_geo}/{len(recs)}')
    still = [r['page'] for r in recs if r['lat'] is None]
    for p in still:
        print('   still:', p)

if __name__ == '__main__':
    main()
