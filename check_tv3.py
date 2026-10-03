"""Check TV catalog source:id format."""
import json

with open('camera_testing/tv_catalog_full.json') as f:
    catalog = json.load(f)
cams = catalog['cameras']

# Check the source field for fintraffic
ff = [c for c in cams if c.get('source') == 'fintraffic']
print(f'fintraffic cams: {len(ff)}')
if ff:
    print(f'First: {ff[0].get("id")}')
    print(f'Source: {ff[0].get("source")}')

# Check first TV in catalog
print()
print('First 10 source:id pairs:')
seen_sources = set()
for c in cams:
    s = c.get('source', '')
    if s and s not in seen_sources:
        seen_sources.add(s)
        cid = c.get('id', '')
        print(f'  {s}::{cid}')
        if len(seen_sources) >= 10:
            break

# Count unique sources
sources = set()
for c in cams:
    s = c.get('source', '')
    if s:
        sources.add(s)
print(f'\nTotal unique sources: {len(sources)}')
print(f'Total cams: {len(cams):,}')
