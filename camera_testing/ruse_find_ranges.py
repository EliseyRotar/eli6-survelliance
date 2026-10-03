"""Ruse/BG IP ranges discovery - use multiple sources."""

import json
import os
import re
import urllib.request
import ssl
import time

OUT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_ruse\ip_ranges"
os.makedirs(OUT, exist_ok=True)


def get(url, timeout=20):
    headers = {'User-Agent': 'Mozilla/5.0 (research)'}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  err {url[:60]}: {str(e)[:80]}")
        return None


# 1. RIPE DB search by AS
print("[RIPE] Searching for ASNs in Ruse...")

# Bulgarian ISP ASNs
BG_ASNS = {
    "AS8866": "Vivacom Bulgaria (BTC)",
    "AS8717": "A1 Bulgaria",
    "AS8242": "Yettel Bulgaria",
    "AS12798": "Bulsatcom",
    "AS9070": "Cooolbox",
    "AS8377": "Spectrum Net",
    "AS29667": "Online Direct",
    "AS204957": "Ruse Cable TV",
    "AS21313": "Megalan BG",
    "AS35773": "Telepoint BG",
    "AS20911": "Net-Surf.net",
    "AS47989": "DCC Bulgaria",
    "AS39184": "Ruse UniData",
    "AS29401": "BTC Net",
    "AS28909": "Trans Tele",
    "AS39135": "BG Connect",
    "AS51539": "STOYANHAYS Net",
    "AS59900": "Ruse Provider",
    "AS31029": "M-Real Net",
    "AS59900": "BG ISP",
    "AS62051": "NetCube",
}


def ripe_search_asn(asn):
    """Search RIPE for prefixes announced by ASN."""
    url = f'https://rest.db.ripe.net/search.json?query=origin%3A{asn}&flags=no-referenced&flags=no-irt&type=inetnum&flags=no-attribute'
    return get(url)


def ripe_search_geoloc():
    """Search RIPE for IPs in Ruse bbox."""
    # Approx bbox: 43.78-43.86 N, 25.88-26.05 E
    url = 'https://rest.db.ripe.net/search.json?query=geoloc:43.78,25.88,43.86,26.05&flags=no-referenced&flags=no-irt&type=inetnum'
    return get(url)


# Test
print("  Testing RIPE...")
data = ripe_search_asn('AS8866')
if data:
    try:
        d = json.loads(data)
        prefixes = []
        for obj in d.get('objects', {}).get('object', []):
            for attr in obj.get('attributes', {}).get('attribute', []):
                if attr.get('name') == 'inetnum':
                    prefixes.append(attr.get('value'))
        print(f"  AS8866 prefix samples: {prefixes[:5]}")
    except Exception:
        pass

# 2. Use bigdatacloud.net free lookup to get Ruse prefixes
print("\n[bdc] Searching for Ruse ranges...")
# Not free API for IP ranges. Try ip2location

# 3. Use RIPE Atlas probes that geo-locate to Ruse?
# 4. Try Bing IP search: bg+ip+ruse

# 5. Use ipdeny.com for BG IPv4 blocks
print("\n[ipdeny.com] Fetching BG prefixes...")
data = get('http://www.ipdeny.com/ipblocks/data/countries/bg.zone')
if data:
    with open(os.path.join(OUT, 'bg.zone'), 'w') as f:
        f.write(data)
    prefixes = [l.strip() for l in data.split('\n') if l.strip() and not l.startswith('#')]
    print(f"  Saved {len(prefixes)} BG prefixes")
    # Sample
    for p in prefixes[:10]:
        print(f"    {p}")

# 6. Use OVH abuse contacts (BG)
print("\n[bgp.he.net] Re-trying with bgp JSON API...")
data = get('https://bgp.he.net/country/BG')
if data:
    with open(os.path.join(OUT, 'bgp_bg.html'), 'w', encoding='utf-8') as f:
        f.write(data)
    # Parse /24 and larger prefixes
    prefixes = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+)', data)
    print(f"  Saved {len(prefixes)} prefixes from bgp.he.net (may be HTML)")
    for p in prefixes[:20]:
        print(f"    {p}")

# 7. Try Hurricane Electric BGP data via JSON
print("\n[HE JSON API]")
data = get('https://bgp.he.net/country/BG/json')
if data:
    with open(os.path.join(OUT, 'bgp_bg.json'), 'w') as f:
        f.write(data)

print("\n[DONE] Check dossier_ruse/ip_ranges for results")
