"""Show missing TV cams."""
import json
from collections import Counter

with open('tv_missing.json') as f:
    missing = json.load(f)
print(f'Total missing: {len(missing):,}')

srcs = Counter(c.get('source', 'unknown') for c in missing)
print('Missing by source:')
for s, c in srcs.most_common(40):
    print(f'  {s}: {c}')
print()
for c in missing[:20]:
    src = c.get('source', '?')
    cid = c.get('id', '?')
    url = (c.get('videoUrl') or c.get('imageUrl') or c.get('sourceUrl') or '')[:60]
    print(f'  {src}::{cid} | url={url}')
