#!/usr/bin/env python3
"""Final aggregate - only sources with >5 cams."""
import csv
import re
from collections import Counter

INPUT = "C:/Users/eli6-admin/Documents/eli6-surveillance/controllable_Webcams.csv"
with open(INPUT, encoding="utf-8", errors="replace") as f:
    rows = list(csv.DictReader(f))
argus = [r for r in rows if "(argus)" in r.get("project_name", "")]

def get_source(notes):
    m = re.search(r"argus_id=([\w_-]+)", notes)
    if not m: return None
    aid = m.group(1)
    if not aid.startswith("opencctv_"): return aid
    parts = aid.split("_")
    rest = parts[1:]
    if len(rest) < 2: return "_".join(rest)
    last = rest[-1]
    is_uuid = bool(re.match(r"^[0-9A-F]{8}-", last, re.IGNORECASE)) or bool(re.match(r"^[0-9a-f]{16,}$", last))
    is_short_code = bool(re.match(r"^[A-Z]{2,3}$", last))
    is_all_digits = last.isdigit()
    if is_uuid or is_all_digits or is_short_code:
        return "_".join(rest[:-1])
    return "_".join(rest)

sources = Counter()
for r in argus:
    src = get_source(r.get("notes", ""))
    if src:
        sources[src] += 1

# Print only sources with count >= 5
big = sorted([(s, c) for s, c in sources.items() if c >= 5], key=lambda x: -x[1])
print(f"=== (argus) SOURCES WITH >=5 CAMS ({len(big)} sources) ===")
print(f"Total (argus) cams: {len(argus)}")
total_big = sum(c for _, c in big)
print(f"Cams in these {len(big)} sources: {total_big} ({100*total_big/len(argus):.1f}%)\n")
for s, c in big:
    print(f"  {c:6}  {s}")
print(f"\n=== Sources with <5 cams: {len(sources) - len(big)} (mostly individual Windy cams) ===")
