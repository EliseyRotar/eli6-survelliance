#!/usr/bin/env python3
"""Final clean argus source analysis."""
import csv
import re
from collections import Counter, defaultdict

INPUT = "C:/Users/eli6-admin/Documents/eli6-surveillance/controllable_Webcams.csv"
with open(INPUT, encoding="utf-8", errors="replace") as f:
    rows = list(csv.DictReader(f))
argus = [r for r in rows if "(argus)" in r.get("project_name", "")]

# Aggregate by the real source name (drop UUIDs/numbers from end)
def get_source(notes):
    m = re.search(r"argus_id=([\w_-]+)", notes)
    if not m: return None
    aid = m.group(1)
    if not aid.startswith("opencctv_"): return aid
    parts = aid.split("_")
    rest = parts[1:]  # drop 'opencctv'
    if len(rest) < 2: return "_".join(rest)
    # Heuristic: drop last segment if it's a UUID, or all-digits, or a short all-caps code (2-3 letters)
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

print(f"=== AGGREGATED (argus_id) SOURCE DISTRIBUTION ({len(sources)} unique sources) ===")
print(f"Total (argus) cams: {len(argus)}")
print(f"Total identified by source: {sum(sources.values())}\n")
for s, c in sources.most_common():
    print(f"  {c:6}  {s}")
