"""Use IP-API + free sources to find Ruse IP ranges.

Strategy: Query for known Ruse fixed-line ISPs in Bulgaria:
- A1 Bulgaria (formerly MobilTel, Mobikom) AS8717
- Vivacom (BTC) AS8866
- Telenor (now Yettel) AS8242
- Bulsatcom
- Net Geoma
- Ruse cable operators

Then use Shodan InternetDB to find live hosts.
"""

import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT = os.path.join(WORKDIR, "dossier_ruse", "ip_ranges")
os.makedirs(OUT, exist_ok=True)


def get(url, timeout=20):
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None


# Sources for IP ranges in BG/Ruse
ASN_QUERIES = [
    ("AS8866", "Vivacom Bulgaria (BTC)"),
    ("AS8717", "A1 Bulgaria"),
    ("AS8242", "Yettel Bulgaria (Telenor)"),
    ("AS12798", "Bulsatcom"),
    ("AS204957", "Ruse Cable TV"),
    ("AS21313", "Megalan"),
    ("AS35773", "Telepoint Bulgaria"),
    ("AS20911", "Net-Surf.net"),
    ("AS47989", "DCC Bulgaria"),
    ("AS39184", "Ruse UniData"),
    ("AS29401", "Bulgarian Telecommunication Company"),
    ("AS28909", "TransTeleCom"),
    ("AS8262", "Evolution Access"),
    ("AS24889", "Monet"),
    ("AS35047", "Abissnet (Albania - close to BG)"),
    ("AS29325", "Eservice"),
]


def get_internetdb(ip):
    """Use Shodan InternetDB - free, no key."""
    try:
        url = f'https://internetdb.shodan.io/{ip}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def main():
    # Save BG ASNs list
    asn_path = os.path.join(OUT, 'asns.json')
    with open(asn_path, 'w') as f:
        json.dump(ASN_QUERIES, f, indent=2)
    print(f"[Ruse IP] Saved {len(ASN_QUERIES)} ASN queries")

    # Try to query RIPE for BG inetnums by AS
    ripe_results = {}
    for asn, name in ASN_QUERIES[:5]:
        print(f"  Querying {asn} ({name})...", end="", flush=True)
        url = f'https://stat.ripe.net/data/dns-chain/data.json?resource={asn}&type=as'
        data = get(url)
        if data:
            try:
                ripe_results[asn] = json.loads(data)
                print(f" OK")
            except Exception:
                print(f" parse err")
        else:
            print(f" no data")
        time.sleep(1)

    # Get BGP announced prefixes for AS8866 (Vivacom - biggest BG ISP)
    print("\n[BGP] Getting Vivacom BG prefixes...")
    bgp_urls = [
        ("https://stat.ripe.net/data/dns-chain/data.json?resource=AS8866&type=as", "AS8866"),
        ("https://stat.ripe.net/data/dns-chain/data.json?resource=AS8717&type=as", "AS8717"),
        ("https://stat.ripe.net/data/dns-chain/data.json?resource=AS8242&type=as", "AS8242"),
    ]
    for url, asn in bgp_urls:
        print(f"  {asn}...", end="", flush=True)
        data = get(url)
        if data:
            with open(os.path.join(OUT, f'{asn.replace("AS", "")}_bgp.json'), 'w') as f:
                f.write(data)
            print(" saved")
        else:
            print(" failed")
        time.sleep(1)

    # Use BGP looking glass via API
    print("\n[BGP] Using bgp.he.net for BG prefixes...")
    bgp_bg = get('https://bgp.he.net/country/BG')
    if bgp_bg:
        with open(os.path.join(OUT, 'bgp_bg.html'), 'w', encoding='utf-8') as f:
            f.write(bgp_bg)
        # Parse IPs
        ips = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+)', bgp_bg)
        print(f"  Found {len(ips)} BG prefixes")
        # Save
        with open(os.path.join(OUT, 'bgp_bg_prefixes.txt'), 'w') as f:
            for ip in ips:
                f.write(ip + '\n')

    # Test internetdb.shodan.io for known Ruse ranges
    # Sample Ruse IPs we don't know yet - try Shodan's hostname search
    print("\n[InternetDB] Testing known Ruse IPs...")
    sample_ips = [
        # Common BG fixed-line ranges
        '79.100.1.1', '79.100.100.1',  # BTC/Vivacom
        '85.130.1.1',                  # BTC
        '87.120.1.1',                  # BTC
        '95.43.1.1',                   # BTC
        '212.5.1.1',                   # BTC
        '77.85.1.1',                   # Vivacom
        '78.83.1.1',                   # BTC
        '83.228.1.1',                  # BTC
        '109.121.1.1',                 # ?
        '213.91.1.1',                  # ?
        '77.71.1.1',                   # ?
    ]
    for ip in sample_ips:
        data = get_internetdb(ip)
        if data:
            print(f"  {ip}: ports={len(data.get('ports', []))}, cpes={len(data.get('cpes', []))}")

    print(f"\n[Ruse IP] Done. Saved to {OUT}")


if __name__ == "__main__":
    main()
