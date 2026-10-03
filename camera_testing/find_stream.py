#!/usr/bin/env python3
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

for fn in ['explore_page_falcons.html', 'explore_player_falcons.html']:
    try:
        with open(rf'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\{fn}', encoding='utf-8') as f:
            h = f.read()
    except FileNotFoundError:
        continue
    print(f'\n=== {fn} ===')
    for pat in [r'(?i)https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
                r'(?i)https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*',
                r'(?i)https?://[^\s"\'<>]*\bhls\b[^\s"\'<>]*',
                r'(?i)https?://[^\s"\'<>]*\bcloudfront\b[^\s"\'<>]*',
                r'(?i)https?://[^\s"\'<>]*\bakamai\b[^\s"\'<>]*',
                r'(?i)https?://[^\s"\'<>]*\bwowza\b[^\s"\'<>]*',
                r'(?i)https?://[^\s"\'<>]*\bmanifest\b[^\s"\'<>]*']:
        for m in re.finditer(pat, h):
            print(f'  URL: {m.group(0)[:250]}')
    # JSON keys
    for kw in ['livecam', 'stream', 'hls', 'm3u8', 'feed', 'player_url']:
        for m in re.finditer(rf'["\'](?:{kw}Slug|{kw}Url|{kw})["\']\s*:\s*["\']([^"\']{{1,200}})', h, re.IGNORECASE):
            print(f'  {kw}: {m.group(1)[:200]}')