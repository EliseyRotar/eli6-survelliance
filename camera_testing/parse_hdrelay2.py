#!/usr/bin/env python3
import re

for fn in ['hdrelay_demos.html', 'hdrelay_golf.html', 'hdrelay_search.html', 'hdrelay_point_loma.html']:
    print(f'\n========== {fn} ==========')
    try:
        with open(f'C:\\Users\\eli6-admin\\Documents\\eli6-surveillance\\camera_testing\\{fn}', encoding='utf-8') as f:
            h = f.read()
    except FileNotFoundError:
        continue
    m = re.search(r'<title>(.*?)</title>', h)
    if m: print(f'Title: {m.group(1)}')

    # Find player URLs (cams.hdrelay.com OR watch.hdrelay.io)
    print('Player URLs:')
    for m in re.finditer(r'(?:player\.html|player/index\.html)[^"\']*', h):
        print(f'  {m.group(0)[:200]}')

    # Find CID_ or cam_ IDs
    cids = set(re.findall(r'CID_[A-Z0-9]+', h))
    cams = set(re.findall(r'cam_[a-zA-Z0-9_]+', h))
    if cids:
        print(f'CID_ IDs: {cids}')
    if cams:
        print(f'cam_ IDs: {cams}')

    # watch.hdrelay.io URLs
    for m in re.finditer(r'https?://watch\.hdrelay\.io/[^\s"\'<>]+', h):
        print(f'  WATCH: {m.group(0)[:200]}')

    # cams.hdrelay.com URLs
    for m in re.finditer(r'https?://cams\.hdrelay\.com/[^\s"\'<>]+', h):
        print(f'  CAMS: {m.group(0)[:200]}')

    # m3u8 / hls / rtmp / ws streams
    for pat in [r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r'rtmp://[^\s"\'<>]+',
                r'wss?://[^\s"\'<>]+', r'https?://[^\s"\'<>]+/hls/[^\s"\'<>]+',
                r'https?://[^\s"\'<>]+/live/[^\s"\'<>]+',
                r'https?://[^\s"\'<>]*\b(?:stream|live|edge|cdn)[^\s"\'<>]+']:
        for m in re.finditer(pat, h, re.IGNORECASE):
            print(f'  STREAM: {m.group(0)[:200]}')