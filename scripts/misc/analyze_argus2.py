#!/usr/bin/env python3
"""Analyze argus_id source distribution."""
import csv
import re
from collections import Counter

INPUT = "C:/Users/eli6-admin/Documents/eli6-surveillance/controllable_Webcams.csv"
with open(INPUT, encoding="utf-8", errors="replace") as f:
    rows = list(csv.DictReader(f))
argus = [r for r in rows if "(argus)" in r.get("project_name", "")]

# Extract argus_id source prefixes
def get_source(notes):
    m = re.search(r"argus_id=([\w_-]+)", notes)
    if m:
        aid = m.group(1)
        # Strip trailing -ID
        parts = aid.split("-")
        # Find the source: after opencctv_/etc, the source name
        if aid.startswith("opencctv_"):
            # opencctv_<source>_<rest> -> source is parts[1], possibly more parts
            # But some sources have multiple segments (e.g. arcgis_cams)
            src = "_".join(parts[1:-1]) if len(parts) > 2 else parts[1]
            return src
        return aid
    return None

sources = Counter()
host_by_source = {}
for r in argus:
    src = get_source(r.get("notes", ""))
    if src:
        sources[src] += 1
        host_by_source.setdefault(src, Counter())[r.get("host", "")] += 1

print("=== TOP 50 argus_id SOURCES (count of cams) ===")
for s, c in sources.most_common(50):
    top_hosts = host_by_source[s].most_common(3)
    host_str = ", ".join(f"{h}({n})" for h, n in top_hosts)
    print(f"  {c:6}  {s:<35} hosts: {host_str}")

# For each, show 1 sample URL pattern
print("\n=== URL PATH PATTERNS BY SOURCE (top 20) ===")
import re
paths = {}
for r in argus:
    src = get_source(r.get("notes", ""))
    if not src: continue
    url = r.get("live_stream_url") or r.get("url") or ""
    # Extract path pattern - remove uuids, numbers
    p = re.sub(r"/[a-f0-9-]{8,}", "/<UUID>", url)
    p = re.sub(r"/\d{4,}", "/<N>", p)
    p = re.sub(r"/[A-Z]\d+-\d+", "/<ID>", p)
    p = re.sub(r"/[a-z]+\d+", "/<ID>", p)
    paths.setdefault(src, Counter())[p] += 1

for s, _ in sources.most_common(20):
    if s in paths:
        top = paths[s].most_common(2)
        for pat, c in top:
            print(f"  [{s}] {c:5}  {pat[:150]}")

# Look for cams WITH actual unique page_title or description
print("\n=== Cams WITH page_title (first 20) ===")
n = 0
for r in argus:
    if r.get("page_title", "").strip():
        print(f"  {r.get('page_title')!r}  |  url: {r.get('live_stream_url', '')[:100]}")
        n += 1
        if n >= 20: break

# Look for cams with non-default lat/lng
print("\n=== Lat/Lng distribution (default vs unique) ===")
ll = Counter()
for r in argus:
    key = (r.get("lat",""), r.get("lon",""))
    ll[key] += 1
print(f"  Unique lat/lng pairs: {len(ll)}")
print(f"  Top 10 most common lat/lng (often defaults):")
for k, c in ll.most_common(10):
    print(f"    {c:6}  lat={k[0]}, lon={k[1]}")
print(f"  Cams with unique lat/lng (singleton): {sum(1 for k, c in ll.items() if c == 1)}")
