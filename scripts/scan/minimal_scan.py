#!/usr/bin/env python3
"""Minimal CVE scanner test"""
import csv, re, urllib.request, ssl
from pathlib import Path

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

# Count targets
targets = set()
with open(CSV_PATH, encoding='utf-8', errors='replace') as f:
    for row in csv.DictReader(f):
        host = row.get('host', '').strip()
        project = row.get('project_name', '').lower()
        if 'alertcalifornia' in project or 'axis' in host.lower():
            targets.add(host)
print(f"Axis targets: {len(targets)}")

# Scan the first target
if targets:
    host = sorted(targets)[0]
    print(f"Scanning: {host}")
    try:
        url = f"http://{host}/axis-cgi/param.cgi?action=get&group=Product"
        resp = urllib.request.urlopen(urllib.request.Request(url, method='GET'), timeout=5, context=ctx)
        body = resp.read().decode('utf-8', errors='replace')
        m = re.search(r'(?i)firmware["\'=:\s]+([\d.]+)', body)
        if m:
            v = m.group(1)
            p = v.split('.')
            vuln = int(p[0]) == 12 and int(p[1]) <= 11
            print(f"Firmware: {v} - Vulnerable: {vuln}")
        else:
            print("No firmware found")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")