# -*- coding: utf-8 -*-
"""Session 46 part 5: retry geocode misses + probe bcfsvc 8443."""
import json
import time
import urllib.request
import urllib.error
import urllib.parse

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
GEO_UA = {"User-Agent": "eli6-surveillance-research/1.0 (webcam mapping)"}


def fetch(url, headers=None, timeout=20):
    hh = dict(UA)
    if headers:
        hh.update(headers)
    req = urllib.request.Request(url, headers=hh)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


print("== bcfsvc/csdcustomer 8443 ==")
for host in ["bcfsvc.bcferries.com", "csdcustomer.bcferries.com"]:
    for port, scheme in [(443, "https"), (8443, "https")]:
        st, h, b = fetch(f"{scheme}://{host}:{port}/" if port != 443 else f"{scheme}://{host}/", timeout=12)
        print(f"  {scheme}://{host}:{port}/ -> {st} {h.get('Content-Type')} {b[:120]!r}" if isinstance(b, bytes) else b)

print("== retry geocode misses ==")
RETRY = {
    "ALF": ["Alliford Bay Ferry Terminal", "Alliford Bay Moresby Island"],
    "BKY": ["Buckley Bay Ferry Terminal", "Buckley Bay Denman Island"],
    "COR": ["Whaletown Ferry Terminal", "Whaletown Cortes Island"],
    "DNE": ["Gravelly Bay Ferry Terminal Denman", "Denman Island East Ferry Terminal"],
    "FUL": ["Fulford Harbour Ferry Terminal", "Fulford Harbour Salt Spring"],
    "GAB": ["Descanso Bay Ferry Terminal", "Gabriola Island Ferry Terminal"],
    "PBB": ["McLoughlin Bay Ferry Terminal Bella Bella", "Bella Bella Ferry Terminal McLoughlin"],
    "POB": ["Otter Bay Ferry Terminal", "Otter Bay Pender Island"],
    "PVB": ["Village Bay Ferry Terminal", "Village Bay Mayne Island"],
    "STB": ["Sturdies Bay Ferry Terminal", "Sturdies Bay Galiano Island"],
    "THT": ["Preedy Harbour Ferry Terminal", "Preedy Harbour Thetis Island"],
}

with open(ROOT + r"\_bcf_geocode.json", encoding="utf-8") as f:
    geocoded = json.load(f)

for code, queries in RETRY.items():
    got = None
    for q in queries:
        url = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + urllib.parse.quote(q)
        st, h, b = fetch(url, headers=GEO_UA, timeout=20)
        time.sleep(1.1)
        try:
            arr = json.loads(b.decode())
        except Exception:
            continue
        if arr:
            got = {"lat": float(arr[0]["lat"]), "lon": float(arr[0]["lon"]), "display": arr[0]["display_name"]}
            break
    if got:
        geocoded[code] = got
        print(f"  {code}: {got['lat']:.5f},{got['lon']:.5f}  {got['display'][:70]}")
    else:
        print(f"  {code}: MISS")

with open(ROOT + r"\_bcf_geocode.json", "w", encoding="utf-8") as f:
    json.dump(geocoded, f, indent=2)
print("total geocoded:", len(geocoded))
print("still missing:", sorted(set(RETRY) - set(geocoded)))
