# -*- coding: utf-8 -*-
"""Session 46 part 4: origin bypass, HSB-NAN oddity, port sweep, geocode."""
import re
import json
import time
import socket
import urllib.request
import urllib.error
import urllib.parse

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch(url, headers=None, timeout=20):
    hh = dict(UA)
    if headers:
        hh.update(headers)
    req = urllib.request.Request(url, headers=hh)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(6000)
    except Exception as e:
        return None, {}, str(e).encode()


print("== HSB-NAN page content ==")
st, h, b = fetch("https://www.bcferries.com/current-conditions/HSB-NAN")
html = b.decode("utf-8", "replace")
# where does 'webcam' appear?
for m in re.finditer(r'.{80}webcam.{80}', html, re.I):
    print(" ctx:", re.sub(r"\s+", " ", m.group(0)))
# any cam images with different pattern
print(" cam-ish:", sorted(set(re.findall(r'cam[A-Za-z0-9_\-\.]+', html))))
print(" ccimg:", sorted(set(re.findall(r'ccimg[^"\']+', html))))
# maybe lazy-loaded via data attr
print(" data-media sample:", re.findall(r'data-media=\'([^\']{0,200})', html)[:3])

print("== origin bypass attempts ==")
# direct IP with Host header
for ip in ["98.158.84.72", "98.158.84.78"]:
    for host in ["cc.bcferries.com", "ccimg.bcferries.com"]:
        st, h, b = fetch(
            f"https://{ip}/cc/support/terminals/cam1_TSA.jpg",
            headers={"Host": host},
        )
        print(f"  https://{ip} Host={host} -> {st} {h.get('Content-Type')} len={len(b)}")

# alternate paths on ccimg
print("== alternate cam paths on ccimg ==")
alts = [
    "/cc/support/terminals/cam1_TSA.JPG",
    "/cc/support/terminals/CAM1_TSA.jpg",
    "/CC/support/terminals/cam1_TSA.jpg",
    "/cc/support/terminals/cam1_TSA.jpg?",
    "/cc/support/terminals/cam1_TSA.jpg?r=1",
    "/cc/support/terminals/cam1_TSA.png",
    "/cc/support/terminals/cam1_TSA.mjpeg",
    "/cc/support/terminals/cam1_TSA.ts",
    "/cc/support/terminals/cam1_TSA.gif",
    "/cc/support/webcam/cam1_TSA.jpg",
    "/cc/support/cams/cam1_TSA.jpg",
    "/cc/support/terminals/tsa/cam1.jpg",
]
for p in alts:
    st, h, b = fetch("https://ccimg.bcferries.com" + p, timeout=10)
    ct = h.get("Content-Type", "")
    ok = st == 200 and ("image" in ct or "video" in ct)
    print(f"  {p} -> {st} {ct} len={len(b)}{' OK' if ok else ''}")

print("== InternetDB sweep 98.158.84.0/24 sample (known hosts) ==")
known = sorted({
    "98.158.84.71", "98.158.84.72", "98.158.84.73", "98.158.84.74", "98.158.84.75",
    "98.158.84.77", "98.158.84.78", "98.158.84.79", "98.158.84.80", "98.158.84.81",
    "98.158.84.87", "98.158.84.90", "98.158.84.92", "98.158.84.93", "98.158.84.94",
    "98.158.84.104", "98.158.84.106", "98.158.84.109", "98.158.84.110", "98.158.84.155",
    "98.158.84.198",
})
port_hits = []
for ip in known:
    st, h, b = fetch(f"https://internetdb.shodan.io/{ip}", timeout=12)
    try:
        d = json.loads(b.decode())
    except Exception:
        print("  fail", ip)
        continue
    ports = d.get("ports", [])
    flag = ""
    if any(p in ports for p in (554, 8000, 8080, 8443, 5000, 5001, 1935)):
        flag = " <== STREAMY"
        port_hits.append({"ip": ip, "ports": ports, "hostnames": d.get("hostnames")})
    print(f"  {ip} ports={ports} hostnames={d.get('hostnames')}{flag}")

print("== Nominatim geocode terminals ==")
# terminal display names from select + cam codes
TERMS = {
    "ALF": "Alliford Bay ferry terminal Haida Gwaii",
    "ALR": "Alert Bay ferry terminal Cormorant Island",
    "BEC": "Bella Coola ferry terminal",
    "BKY": "Buckley Bay ferry terminal Denman Island",
    "BOW": "Snug Cove ferry terminal Bowen Island",
    "BTW": "Brentwood Bay ferry terminal",
    "CAM": "Campbell River ferry terminal",
    "CFT": "Crofton ferry terminal",
    "CHM": "Chemainus ferry terminal",
    "CMX": "Little River ferry terminal Comox",
    "COR": "Whaletown ferry terminal Cortes Island",
    "DNE": "Gravelly Bay ferry terminal Denman Island East",
    "DNM": "Denman Island West ferry terminal",
    "DUK": "Duke Point ferry terminal Nanaimo",
    "ERL": "Earls Cove ferry terminal Sunshine Coast",
    "FUL": "Fulford Harbour ferry terminal Salt Spring Island",
    "GAB": "Descanso Bay ferry terminal Gabriola Island",
    "HER": "Heriot Bay ferry terminal Quadra Island",
    "HRN": "Shingle Spit ferry terminal Hornby Island",
    "HSB": "Horseshoe Bay ferry terminal West Vancouver",
    "KPR": "Telegraph Harbour ferry terminal Penelakut Island",
    "LNG": "Langdale ferry terminal Sunshine Coast",
    "MCN": "Port McNeill ferry terminal",
    "MIL": "Mill Bay ferry terminal",
    "NAH": "Nanaimo Harbour ferry terminal",
    "NAN": "Departure Bay ferry terminal Nanaimo",
    "PBB": "McLoughlin Bay ferry terminal Bella Bella",
    "POB": "Otter Bay ferry terminal Pender Island",
    "POF": "Ocean Falls ferry terminal",
    "PPH": "Bear Cove ferry terminal Port Hardy",
    "PPR": "Prince Rupert ferry terminal",
    "PSK": "Skidegate ferry terminal Graham Island",
    "PVB": "Village Bay ferry terminal Mayne Island",
    "PWR": "Westview ferry terminal Powell River",
    "QDR": "Quathiaski Cove ferry terminal Quadra Island",
    "SLT": "Saltery Bay ferry terminal Powell River",
    "STB": "Sturdies Bay ferry terminal Galiano Island",
    "SWB": "Swartz Bay ferry terminal Victoria",
    "TEX": "Blubber Bay ferry terminal Texada Island",
    "THT": "Preedy Harbour ferry terminal Thetis Island",
    "TSA": "Tsawwassen ferry terminal",
    "VES": "Vesuvius Bay ferry terminal Salt Spring Island",
}
geocoded = {}
for code, q in TERMS.items():
    url = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + urllib.parse.quote(q)
    st, h, b = fetch(url, headers={"User-Agent": "eli6-surveillance-research/1.0 (webcam mapping)"}, timeout=20)
    try:
        arr = json.loads(b.decode())
        if arr:
            geocoded[code] = {"lat": float(arr[0]["lat"]), "lon": float(arr[0]["lon"]), "display": arr[0]["display_name"]}
            print(f"  {code}: {geocoded[code]['lat']:.5f},{geocoded[code]['lon']:.5f}  {arr[0]['display_name'][:70]}")
        else:
            print(f"  {code}: MISS")
    except Exception as e:
        print(f"  {code}: ERR {e} {b[:80]}")
    time.sleep(1.1)

with open(ROOT + r"\_bcf_geocode.json", "w", encoding="utf-8") as f:
    json.dump(geocoded, f, indent=2)
print("geocoded", len(geocoded), "of", len(TERMS))
print("port_hits:", port_hits)
print("done")
