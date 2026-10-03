#!/usr/bin/env python3
"""Analyze (argus) cams in the CSV."""
import csv
from collections import Counter

INPUT = "C:/Users/eli6-admin/Documents/eli6-surveillance/controllable_Webcams.csv"

with open(INPUT, encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    rows = [r for r in reader]

argus = [r for r in rows if "(argus)" in r.get("project_name", "")]
print(f"Total rows: {len(rows)}")
print(f"Total (argus) rows: {len(argus)}\n")

# Group by host
hosts = Counter(r.get("host", "") for r in argus)
print("=== Top 30 hosts for (argus) cams ===")
for h, c in hosts.most_common(30):
    print(f"  {c:6}  {h!r}")

# Group by project_name pattern
names = Counter(r.get("project_name", "") for r in argus)
print("\n=== Top 30 project_name patterns ===")
for n, c in names.most_common(30):
    print(f"  {c:6}  {n!r}")

# Group by country
countries = Counter(r.get("country", "") for r in argus)
print("\n=== Top 20 countries ===")
for c, n in countries.most_common(20):
    print(f"  {n:6}  {c!r}")

# Sample 5 rows
print("\n=== 5 SAMPLE ROWS (first argus) ===")
for r in argus[:5]:
    print({k: r.get(k, "") for k in [
        "project_name","url","live_stream_url","type","live_status",
        "page_title","description","category","likely_subject","brand","model",
        "country","region","city","address","lat","lon","host",
        "isp","org","asn","reverse_dns","notes"
    ]})
    print()

# Look at 25 diverse samples (different hosts/names)
print("\n=== 25 DIVERSE SAMPLES ===")
seen_keys = set()
samples = []
for r in argus:
    key = (r.get("host",""), r.get("project_name",""))
    if key in seen_keys: continue
    seen_keys.add(key)
    samples.append(r)
    if len(samples) >= 25: break

for r in samples:
    print(f"---")
    print(f"  name: {r.get('project_name')}")
    print(f"  host: {r.get('host')}")
    print(f"  url: {r.get('url')}")
    print(f"  live_stream_url: {r.get('live_stream_url')}")
    print(f"  type: {r.get('type')}")
    print(f"  page_title: {r.get('page_title')}")
    print(f"  desc: {r.get('description')[:120]}")
    print(f"  cat: {r.get('category')} | subj: {r.get('likely_subject')} | brand: {r.get('brand')} | model: {r.get('model')}")
    print(f"  country: {r.get('country')} | region: {r.get('region')} | city: {r.get('city')} | addr: {r.get('address')}")
    print(f"  lat/lon: {r.get('lat')},{r.get('lon')}")
    print(f"  isp: {r.get('isp')} | org: {r.get('org')} | asn: {r.get('asn')}")
    print(f"  rDNS: {r.get('reverse_dns')}")
    print(f"  notes: {r.get('notes')[:200]}")
