"""Bulk RTSP probe - find endpoints, save to file for full probe."""
import csv
import os
import time
import json
import re
import socket
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

import glob

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break


def tcp_probe(host, port, timeout=3):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        s.send(b'OPTIONS rtsp://%s:%d/ RTSP/1.0\r\nCSeq: 1\r\n\r\n' % (host.encode(), port))
        data = s.recv(2048)
        s.close()
        return data.decode('utf-8', errors='replace')
    except Exception as e:
        return None


def main():
    csv.field_size_limit(2**31 - 1)
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])

    # Get unique IPs from CSV
    ips = set()
    for url in existing:
        m = re.match(r'https?://(\d+\.\d+\.\d+\.\d+)', url)
        if m:
            ips.add(m.group(1))
    print(f'CSV has {len(ips):,} unique IPs')

    # Filter to known cam-related ports and probe port 554
    print(f'\n[RTSP Scan] Probing {len(ips)} IPs on port 554...')
    found = []
    ip_list = list(ips)
    with open('rtsp_endpoints.jsonl', 'w', encoding='utf-8') as f_out:
        with ThreadPoolExecutor(max_workers=20) as ex:
            def probe(ip):
                resp = tcp_probe(ip, 554, timeout=3)
                if resp and 'RTSP' in resp:
                    return (ip, resp)
                return None
            futs = {ex.submit(probe, ip): ip for ip in ip_list}
            n_done = 0
            for f in as_completed(futs):
                try:
                    r = f.result(timeout=6)
                    if r:
                        found.append(r)
                        f_out.write(json.dumps(r) + '\n')
                        f_out.flush()
                except Exception:
                    pass
                n_done += 1
                if n_done % 100 == 0:
                    print(f'  {n_done}/{len(ip_list)} probed, {len(found)} found')

    print(f'\n[RESULT] Found {len(found)} RTSP endpoints')
    print(f'  Saved to rtsp_endpoints.jsonl')


if __name__ == '__main__':
    main()
