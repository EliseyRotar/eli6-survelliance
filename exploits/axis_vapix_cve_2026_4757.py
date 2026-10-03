#!/usr/bin/env python3
"""CVE-2026-4757: Axis VAPIX API Parameter RCE Scanner
CVSS: 7.2 HIGH | AXIS OS 12.0.0-12.11.43 | 482 targets in DB"""
import csv, json, re, urllib.request, ssl, time
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def scan():
    results = []
    targets = set()
    with open(CSV_PATH, encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if 'alertcalifornia' in row.get('project_name', '').lower():
                targets.add(row.get('host', ''))
    print(f"Scanning {len(targets)} ALERTCalifornia Axis cameras for CVE-2026-4757...")
    for host in sorted(targets):
        result = {'host': host, 'vulnerable': False, 'version': 'unknown'}
        try:
            url = f"http://{host}/axis-cgi/param.cgi?action=get&group=Product"
            resp = urllib.request.urlopen(urllib.request.Request(url, method='GET'), timeout=8, context=ctx)
            body = resp.read().decode('utf-8', errors='replace')
            m = re.search(r'(?i)firmware["\'=:\s]+([\d.]+)', body)
            if m:
                v = m.group(1); result['version'] = v
                p = v.split('.')
                if len(p) >= 2 and int(p[0]) == 12 and int(p[1]) <= 11:
                    result['vulnerable'] = True
        except Exception: pass
        results.append(result)
    vuln = [r for r in results if r['vulnerable']]
    print(f"Results: {len(vuln)}/{len(results)} vulnerable")
    for r in vuln[:10]: print(f"  {r['host']} — AXIS OS {r['version']}")
    return results

if __name__ == '__main__': scan()
