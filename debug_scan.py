#!/usr/bin/env python3
"""Debug version - check targets and run quick scan"""
import csv, json, re, urllib.request, ssl, socket, struct, time
from pathlib import Path

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

print("Reading CSV...")
with open(CSV_PATH, encoding='utf-8', errors='replace') as f:
    rows = list(csv.DictReader(f))
print(f"CSV rows: {len(rows)}")

# Count targets
targets = set()
with open(CSV_PATH, encoding='utf-8', errors='replace') as f:
    for row in csv.DictReader(f):
        host = row.get('host', '').strip()
        project = row.get('project_name', '').lower()
        if 'alertcalifornia' in project or 'axis' in host.lower():
            targets.add(host)
print(f"Axis targets: {len(targets)}")

targets2 = set()
with open(CSV_PATH, encoding='utf-8', errors='replace') as f:
    for row in csv.DictReader(f):
        host = row.get('host', '').strip()
        if 'abckam' in host.lower():
            targets2.add(host)
print(f"AntMedia targets: {len(targets2)}")

targets3 = set()
with open(CSV_PATH, encoding='utf-8', errors='replace') as f:
    for row in csv.DictReader(f):
        host = row.get('host', '').strip()
        if 'vivotek' in host.lower():
            targets3.add(host)
print(f"Vivotek targets: {len(targets3)}")

targets4 = set()
with open(CSV_PATH, encoding='utf-8', errors='replace') as f:
    for row in csv.DictReader(f):
        host = row.get('host', '').strip()
        project = row.get('project_name', '').lower()
        if 'abckam' in host.lower() or 'dahua' in project:
            targets4.add(host)
print(f"Dahua targets: {len(targets4)}")

print("\nQuick scan test on first few hosts...")
# Test Axis
if targets:
    host = sorted(targets)[0]
    print(f"Testing Axis: {host}")
    try:
        url = f"http://{host}/axis-cgi/param.cgi?action=get&group=Product"
        resp = urllib.request.urlopen(urllib.request.Request(url, method='GET'), timeout=5, context=ctx)
        body = resp.read().decode('utf-8', errors='replace')
        m = re.search(r'(?i)firmware["\'=:\s]+([\d.]+)', body)
        if m:
            print(f"  Firmware: {m.group(1)} - VULNERABLE" if int(m.group(1).split('.')[1]) <= 11 else "  Not vulnerable")
        else:
            print("  No firmware found")
    except Exception as e:
        print(f"  Error: {e}")

# Test AntMedia JMX
if targets2:
    host = sorted(targets2)[0]
    print(f"Testing AntMedia JMX: {host}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        r = s.connect_ex((host, 5599))
        s.close()
        print(f"  Port 5599 open: {r == 0}")
    except Exception as e:
        print(f"  Error: {e}")

print("\nDone.")