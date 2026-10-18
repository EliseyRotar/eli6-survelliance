import re, glob, os, subprocess

TEMP = os.environ['TEMP']
for p in sorted(glob.glob(TEMP + r'\gip_*.html')) + [TEMP + r'\zumaia.html']:
    if p.endswith('gip_webcams.html'):
        continue
    h = open(p, encoding='utf-8', errors='replace').read()
    h1 = [re.sub(r'\s+', ' ', x).strip() for x in re.findall(r'<h1[^>]*>(.*?)</h1>', h, re.S)]
    ttl = re.findall(r'<title>(.*?)</title>', h, re.S)
    geo_lat = re.findall(r'latitude["\s:=]+(-?\d+\.\d+)', h, re.I)[:3]
    geo_lon = re.findall(r'longitude["\s:=]+(-?\d+\.\d+)', h, re.I)[:3]
    pairs = re.findall(r'\b(4[23]\.\d{4,})\s*[;,]?\s*(-?[012]\.\d{4,})', h)[:3]
    print(os.path.basename(p))
    print('   h1:', h1[:2])
    print('   geo:', geo_lat, geo_lon, pairs)
    print('   title:', re.sub(r'\s+', ' ', ttl[0]).strip()[:90] if ttl else None)

print('\n-- zumaia stream variants --')
for name in ('GIP_zumaia2', 'GIP_zumaia_169', 'GIP_zumaia', 'GIP_zumaia2_169'):
    url = f'https://58f14c0895a20.streamlock.net/camaramar/{name}.stream/playlist.m3u8'
    r = subprocess.run(['curl.exe', '-s', '-o', 'NUL', '-w', '%{http_code} %{size_download}', '--max-time', '20', '-A', 'Mozilla/5.0', url],
                       capture_output=True, text=True)
    print(name, r.stdout)
