"""Analyze missing TV cams - which have direct URLs vs only landing pages."""
import json
from collections import Counter

with open('tv_missing.json') as f:
    missing = json.load(f)
print(f'Total missing: {len(missing):,}')

# Group by what kind of URL they have
direct = 0  # Has direct video/image URL
youtube = 0  # YouTube ID
youtube_chan = 0  # YouTube channel
generic = 0  # Generic landing page
none_url = 0  # No URL

for c in missing:
    vu = c.get('videoUrl', '')
    iu = c.get('imageUrl', '')
    pu = c.get('playerUrl', '')
    yt = c.get('youtubeVideoId', '')
    ipc = c.get('ipcamliveAlias', '')
    su = c.get('sourceUrl', '')

    has_direct = bool(vu or iu or pu or ipc)
    has_yt_id = bool(yt) and 'watch' not in (yt or '').lower()
    has_yt_chan = 'youtube.com/@' in (su or '') or 'youtube.com/@' in (iu or '')

    if has_direct:
        direct += 1
    elif has_yt_id:
        youtube += 1
    elif has_yt_chan:
        youtube_chan += 1
    elif su:
        generic += 1
    else:
        none_url += 1

print(f'\nURL type breakdown:')
print(f'  Direct (video/image/player/ipcam): {direct}')
print(f'  YouTube ID: {youtube}')
print(f'  YouTube channel: {youtube_chan}')
print(f'  Generic landing page: {generic}')
print(f'  No URL: {none_url}')

# Cams with direct URLs - these are the valuable ones
print(f'\nValuable missing cams (with direct URL):')
val = []
for c in missing:
    vu = c.get('videoUrl', '')
    iu = c.get('imageUrl', '')
    pu = c.get('playerUrl', '')
    ipc = c.get('ipcamliveAlias', '')
    if vu or iu or pu or ipc:
        val.append(c)
print(f'  {len(val):,}')

# Show sample
for c in val[:30]:
    src = c.get('source', '?')
    cid = c.get('id', '?')
    url = (c.get('videoUrl') or c.get('imageUrl') or c.get('playerUrl') or '')[:80]
    print(f'  {src}::{cid} | {url}')
