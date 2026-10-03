"""
Extract ALL hosts from CSV to build a comprehensive host frequency list.
Used to identify what host->geo mappings we need to build.
"""
import csv
from collections import Counter

CSV_PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv"

hosts = Counter()
hosts_by_tld = {}
tlds = Counter()

with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    COL_HOST = header.index('host')
    for row in reader:
        h = row[COL_HOST] if COL_HOST < len(row) else ''
        if h:
            hosts[h] += 1
            parts = h.split('.')
            if len(parts) >= 2:
                tld = parts[-1]
                tlds[tld] += 1
                hosts_by_tld.setdefault(tld, Counter())[h] += 1

print(f"Total unique hosts: {len(hosts)}")
print(f"Total cams with host: {sum(hosts.values())}")
print()
print("Top 50 TLDs:")
for tld, c in tlds.most_common(50):
    print(f"  {c:>8}  .{tld}")
print()
print("Top 50 hosts (with count):")
for h, c in hosts.most_common(50):
    print(f"  {c:>8}  {h}")
