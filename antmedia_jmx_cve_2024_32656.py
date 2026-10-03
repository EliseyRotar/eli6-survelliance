#!/usr/bin/env python3
"""CVE-2024-32656: Ant Media Server JMX Privilege Escalation Scanner
CVSS: 9.8 CRITICAL | Port 5599 | 538 abckam hosts in DB"""
import csv, json, socket, urllib.request, ssl
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def scan():
    targets = set()
    with open(CSV_PATH, encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if 'abckam' in row.get('host', ''): targets.add(row['host'])
    print(f"Scanning {len(targets)} abckam hosts for CVE-2024-32656 JMX (port 5599)...")
    results = []
    for host in sorted(targets):
        result = {'host': host, 'jmx_open': False, 'jmx_auth': False}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3); r = s.connect_ex((host, 5599)); s.close()
            if r == 0:
                result['jmx_open'] = True
                for ep in [f"http://{host}:5599/jolokia/", f"http://{host}:5599/jmxrmi"]:
                    try:
                        resp = urllib.request.urlopen(urllib.request.Request(ep), timeout=3, context=ctx)
                        if resp.status == 200: result['jmx_auth'] = True; break
                    except urllib.error.HTTPError as e:
                        if e.code in (200, 401, 403): result['jmx_auth'] = True; break
                    except Exception: pass
        except Exception: pass
        results.append(result)
    open_jmx = [r for r in results if r['jmx_open']]
    print(f"Results: {len(open_jmx)}/{len(results)} have port 5599 open")
    for r in open_jmx[:10]: print(f"  {r['host']} — JMX {'AUTH' if r['jmx_auth'] else 'NO AUTH'}")
    return results

if __name__ == '__main__': scan()
