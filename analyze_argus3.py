#!/usr/bin/env python3
"""Get a complete breakdown of argus source distribution and patterns."""
import csv
import re
from collections import Counter, defaultdict

INPUT = "C:/Users/eli6-admin/Documents/eli6-surveillance/controllable_Webcams.csv"
with open(INPUT, encoding="utf-8", errors="replace") as f:
    rows = list(csv.DictReader(f))
argus = [r for r in rows if "(argus)" in r.get("project_name", "")]

# More accurate argus_id source extraction
# Format: argus_id=opencctv_<source_a>_<source_b>_<specific_id>
# Or: argus_id=opencctv_<source>_<id>
# Or: argus_id=opencctv_<a>_<b>_<c>_<id>
def get_full_source(notes):
    m = re.search(r"argus_id=([\w_-]+)", notes)
    if not m: return None
    aid = m.group(1)
    if not aid.startswith("opencctv_"): return aid
    parts = aid.split("_")
    # Drop "opencctv" prefix
    rest = parts[1:]
    # If last segment looks like an ID (alphanumeric short), drop it
    # The source name is everything except the last segment
    if len(rest) >= 2:
        # Last segment is the unique id (often a number or short code)
        last = rest[-1]
        # Heuristic: id often has digits and is short
        if re.match(r"^[a-zA-Z0-9-]+$", last) and len(last) <= 30:
            # Check if it looks like a source suffix (e.g., "HK" "NV" "IA")
            # Heuristic: if all caps 2-3 letters OR ends with number
            if re.match(r"^[A-Z]{2,3}$", last) or re.search(r"\d", last):
                src = "_".join(rest[:-1])
                return src
    return "_".join(rest[:-1]) if len(rest) >= 2 else "_".join(rest)

sources = Counter()
host_for_source = defaultdict(Counter)
sample_url = {}
for r in argus:
    src = get_full_source(r.get("notes", ""))
    if not src: continue
    sources[src] += 1
    host_for_source[src][r.get("host", "")[:40]] += 1
    if src not in sample_url:
        sample_url[src] = r.get("live_stream_url") or r.get("url", "")

print(f"Total (argus) cams: {len(argus)}")
print(f"Unique sources identified: {len(sources)}\n")
print("=== COMPLETE SOURCE LIST (count, source, top host, sample URL) ===")
for s, c in sorted(sources.items(), key=lambda x: -x[1]):
    top_h = host_for_source[s].most_common(1)[0]
    url = sample_url[s][:130]
    print(f"  {c:6}  {s:<40} | host: {top_h[0]:<35} | url: {url}")
