"""Check catalog sources."""
import json
from collections import Counter

with open('camera_testing/tv_catalog_full.json', encoding='utf-8') as f:
    cat = json.load(f)
print(f'Catalog: {len(cat["cameras"]):,} cams')

sources = Counter(c.get('source', 'unknown') for c in cat['cameras'])
print(f'Top 20 sources:')
for s, c in sources.most_common(20):
    print(f'  {s}: {c}')
