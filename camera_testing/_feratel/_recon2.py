import re, json, os, sys, html as htmllib

D = os.path.dirname(os.path.abspath(__file__))

def parse(fn):
    src = open(os.path.join(D, fn), encoding='utf-8', errors='replace').read()
    print(f'===== {fn} ({len(src)} bytes) =====')

    # titles
    t = re.search(r'<title>(.*?)</title>', src, re.S)
    print('title:', htmllib.unescape(t.group(1)) if t else None)

    # geo meta
    for pat in [r'<meta[^>]+name="geo\.(latitude|longitude|position)"[^>]+content="([^"]+)"',
                r'"latitude"?\s*:\s*"?(-?\d+\.\d+)', r'"longitude"?\s*:\s*"?(-?\d+\.\d+)']:
        m = re.findall(pat, src)
        if m:
            print('geo-pat', pat[:40], '->', m[:6])

    # json-ld
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', src, re.S):
        print('JSON-LD:', m[:600])

    # media urls
    urls = sorted(set(re.findall(r'https?://[^"\'\s\\]+?\.(?:m3u8|mp4|flv|f4v|ts|mjpg|jpeg|jpg|png)(?:\?[^"\'\s\\]*)?', src, re.I)))
    print('MEDIA URLS (%d):' % len(urls))
    for u in urls[:40]:
        print('   ', u[:200])

    # host-path patterns without extension
    for pat in [r'https?://[^"\'\s\\]+webtv[^"\'\s\\]*', r'https?://[^"\'\s\\]+trafficvision[^"\'\s\\]*',
                r'https?://stsfc[^"\'\s\\]*', r'https?://wtvpictfc[^"\'\s\\]*']:
        for u in sorted(set(re.findall(pat, src, re.I)))[:15]:
            print('HOSTPAT:', u[:200])

    # astro island props (component props are HTML-escaped JSON)
    for m in re.findall(r'props="([^"]+)"', src)[:20]:
        try:
            p = json.loads(m.replace('&quot;', '"').replace('&amp;', '&').replace('&#39;', "'"))
            s = json.dumps(p, ensure_ascii=False)
            print('ISLAND PROPS:', s[:700])
        except Exception as e:
            print('island props raw:', m[:200])

    # data in window or inline scripts
    for m in re.findall(r'window\.([A-Za-z0-9_]+)\s*=\s*(\{.*?\});', src, re.S)[:10]:
        print('WINDOW', m[0], '=', m[1][:400])

    # lat/lon generic
    for m in sorted(set(re.findall(r'"(?:lat|lng|lon|latitude|longitude)"\s*:\s*(-?\d+\.\d{3,})', src)))[:20]:
        print('LATLNG:', m)

    # find components (astro islands) used
    comps = sorted(set(re.findall(r'component-url="([^"]+)"', src)))
    print('ISLAND COMPONENTS:', comps)


for fn in sys.argv[1:] or ['cam1.html', 'cam2.html']:
    parse(fn)
