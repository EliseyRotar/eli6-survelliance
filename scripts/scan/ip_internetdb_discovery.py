"""Fresh webcam discovery from Shodan InternetDB.

Strategy: probe random /16 prefixes that we haven't covered. InternetDB returns
{cpes, ports, tags, vulns} for each IP. We can use it to find fresh webcams
on residential networks without scanning every IP.
"""
import os
import csv
import time
import json
import random
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

import glob

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break
if not CSV_PATH:
    print('CSV not found')
    exit(1)
print(f'CSV: {CSV_PATH}')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def internetdb(ip, timeout=10):
    """Shodan InternetDB - free, no key."""
    try:
        url = f'https://internetdb.shodan.io/{ip}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = json.loads(r.read())
            return data
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return {'error': e.code}
    except Exception as e:
        return {'error': str(e)[:100]}


def main():
    # Load CSV
    csv.field_size_limit(2**31 - 1)
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  CSV has {len(existing):,} URLs')

    # Get list of IPs from CSV
    import re as _re
    ips = set()
    for url in existing:
        m = _re.match(r'https?://(\d+\.\d+\.\d+\.\d+)', url)
        if m:
            ips.add(m.group(1))
    print(f'  CSV has {len(ips):,} unique IPs')

    # Find known prefixes
    existing_prefixes = set()
    for ip in ips:
        a, b, c = ip.split('.')[:3]
        existing_prefixes.add(f'{a}.{b}.{c}')

    # Top residential /16 prefixes (from camera-internet scan data)
    resi_16 = [
        '110.50.', '110.66.', '110.87.', '111.65.', '111.67.',
        '112.5.', '112.6.', '112.7.', '112.8.', '112.9.', '112.10.',
        '113.108.', '113.109.', '113.110.', '113.111.', '114.32.', '114.33.',
        '115.74.', '115.75.', '115.76.', '115.77.', '115.78.', '115.79.',
        '116.93.', '116.94.', '116.95.', '116.96.', '116.97.', '116.98.', '116.99.',
        '117.1.', '117.2.', '117.3.', '117.4.', '117.5.', '117.6.', '117.7.', '117.8.', '117.9.',
        '118.68.', '118.69.', '118.70.', '118.71.', '118.72.', '118.73.', '118.74.', '118.75.',
        '119.0.', '119.1.', '119.2.', '119.3.', '119.4.', '119.5.', '119.6.', '119.7.',
        '120.0.', '120.1.', '120.2.', '120.3.', '120.4.', '120.5.', '120.6.', '120.7.',
        '121.0.', '121.1.', '121.2.', '121.3.', '121.4.', '121.5.', '121.6.', '121.7.',
        '122.0.', '122.1.', '122.2.', '122.3.', '122.4.', '122.5.', '122.6.', '122.7.',
        '123.16.', '123.17.', '123.18.', '123.19.', '123.20.', '123.21.', '123.22.', '123.23.',
        '124.30.', '124.31.', '124.32.', '124.33.', '124.34.', '124.35.', '124.36.', '124.37.',
        '125.20.', '125.21.', '125.22.', '125.23.', '125.24.', '125.25.', '125.26.', '125.27.',
        '175.192.', '175.193.', '175.194.', '175.195.', '175.196.', '175.197.',
        '210.13.', '210.14.', '210.15.', '210.16.', '210.17.', '210.18.', '210.19.',
        '211.136.', '211.137.', '211.138.', '211.139.', '211.140.', '211.141.',
        '218.0.', '218.1.', '218.2.', '218.3.', '218.4.', '218.5.', '218.6.', '218.7.',
        '219.0.', '219.1.', '219.2.', '219.3.', '219.4.', '219.5.', '219.6.', '219.7.',
        '220.0.', '220.1.', '220.2.', '220.3.', '220.4.', '220.5.', '220.6.', '220.7.',
        '221.0.', '221.1.', '221.2.', '221.3.', '221.4.', '221.5.', '221.6.', '221.7.',
        '222.0.', '222.1.', '222.2.', '222.3.', '222.4.', '222.5.', '222.6.', '222.7.',
        '58.32.', '58.33.', '58.34.', '58.35.', '58.36.', '58.37.', '58.38.', '58.39.',
        '59.32.', '59.33.', '59.34.', '59.35.', '59.36.', '59.37.', '59.38.', '59.39.',
        '60.0.', '60.1.', '60.2.', '60.3.', '60.4.', '60.5.', '60.6.', '60.7.',
        '61.135.', '61.136.', '61.137.', '61.138.', '61.139.', '61.140.', '61.141.',
        '85.105.', '85.106.', '85.107.', '85.108.', '85.109.', '85.110.',
    ]

    # Save these prefixes
    print(f'\nLoaded {len(resi_16)} /16 residential prefixes')

    # For each /16, we have 256 /24s, each /24 has 256 IPs = 65,536 IPs per /16
    # InternetDB doesn't accept bulk queries, so we'd need to do per-IP
    # That's 1,000,000+ requests - too many
    # Instead, let me check: does InternetDB have a bulk endpoint?

    # Try InternetDB bulk endpoint
    test_url = 'https://internetdb.shodan.io/'
    status, ct, body = None, None, None
    try:
        req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            status = r.status
            ct = r.headers.get('Content-Type', '')
            body = r.read(200)
    except Exception as e:
        print(f'  Root InternetDB: {e}')

    print(f'  Root InternetDB: {status} {ct} {body[:100] if body else b""}')

    # Use unique random IPs from residential ranges that aren't in our list
    new_ips = []
    random.seed(42)
    for prefix in resi_16:
        for _ in range(20):  # 20 IPs per prefix = 2000 IPs total
            a, b, _ = prefix.split('.')
            c = random.randint(0, 255)
            d = random.randint(1, 254)
            ip = f'{a}.{b}.{c}.{d}'
            if ip not in ips:
                new_ips.append(ip)

    print(f'\n  Total random IPs to query InternetDB: {len(new_ips):,}')

    # Probe InternetDB in parallel
    found_webcams = []
    with open('internetdb_results.jsonl', 'w', encoding='utf-8') as f_out:
        def query_one(ip):
            data = internetdb(ip, timeout=10)
            if data and not data.get('error'):
                f_out.write(json.dumps(data) + '\n')
                # Check for webcams
                tags = data.get('tags', [])
                cpes = data.get('cpes', [])
                ports = data.get('ports', [])
                is_webcam = (
                    'webcam' in str(cpes).lower() or
                    'ipcam' in str(cpes).lower() or
                    'camera' in str(cpes).lower() or
                    80 in ports or 8080 in ports or 8081 in ports or 554 in ports
                )
                if is_webcam:
                    return (ip, data)
            return None

        with ThreadPoolExecutor(max_workers=20) as ex:
            futs = {ex.submit(query_one, ip): ip for ip in new_ips}
            for f in as_completed(futs):
                try:
                    r = f.result(timeout=15)
                    if r:
                        found_webcams.append(r)
                except Exception as e:
                    pass
                if len(found_webcams) % 10 == 0 and found_webcams:
                    print(f'  Found {len(found_webcams)} webcams so far')

    print(f'\n[RESULT] {len(found_webcams)} webcams found via InternetDB')
    for ip, d in found_webcams[:20]:
        ports = d.get('ports', [])
        cpes = d.get('cpes', [])
        print(f'  {ip}: ports={ports} cpes={cpes[:3]}')


if __name__ == '__main__':
    main()
