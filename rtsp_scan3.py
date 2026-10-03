"""Aggressive RTSP probe - check all cam IPs in our CSV on multiple RTSP paths.

Catches cams where the URL is HTTP/MJPEG but the host also runs RTSP.
"""
import socket
import time
import json
import re
import os
import sys
import csv
import glob
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# Force unbuffered
sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break
if not CSV_PATH:
    print('CSV not found')
    exit(1)
print(f'CSV: {CSV_PATH}')


def tcp_rtsp_probe(host, port, timeout=3):
    """Probe RTSP OPTIONS."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        s.send(b'OPTIONS rtsp://%s:%d/ RTSP/1.0\r\nCSeq: 1\r\n\r\n' % (host.encode(), port))
        data = s.recv(2048)
        s.close()
        return data.decode('utf-8', errors='replace')[:300]
    except Exception as e:
        return None


def main():
    csv.field_size_limit(2**31 - 1)
    ips = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            url = row.get('url', '') or ''
            m = re.match(r'(?:rtsp|http)s?://(?:[^@]+@)?(\d+\.\d+\.\d+\.\d+)', url)
            if m:
                ips.add(m.group(1))
    print(f'[RTSP] {len(ips)} unique IPs to probe')

    # Load already-found
    found_ips = set()
    if os.path.exists('rtsp_endpoints.jsonl'):
        with open('rtsp_endpoints.jsonl', 'r') as f:
            for line in f:
                try:
                    r = json.loads(line)
                    found_ips.add(r[0])
                except:
                    pass
    print(f'  Already found: {len(found_ips)}')

    # Probe IPs not yet found
    to_probe = sorted(ips - found_ips)
    print(f'  To probe: {len(to_probe)}')

    # Probe in parallel
    new_found = []
    out_file = open('rtsp_endpoints.jsonl', 'a', encoding='utf-8', buffering=1)
    with ThreadPoolExecutor(max_workers=20) as ex:
        def probe(ip):
            resp = tcp_rtsp_probe(ip, 554, timeout=3)
            if resp and 'RTSP' in resp:
                return (ip, resp)
            return None
        futs = {ex.submit(probe, ip): ip for ip in to_probe}
        n_done = 0
        for f in as_completed(futs):
            try:
                r = f.result(timeout=6)
                if r:
                    new_found.append(r)
                    out_file.write(json.dumps(r) + '\n')
            except Exception:
                pass
            n_done += 1
            if n_done % 100 == 0:
                print(f'  {n_done}/{len(to_probe)} probed, {len(new_found)} new', flush=True)
    out_file.close()

    print(f'\n[RTSP] New endpoints: {len(new_found)}')
    print(f'  Total endpoints: {len(found_ips) + len(new_found)}')


if __name__ == '__main__':
    main()
