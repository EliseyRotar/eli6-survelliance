"""Check fl511 data."""
import json

with open('fl511_cams_with_live.json', encoding='utf-8') as f:
    data = json.load(f)
print(f'Total: {len(data):,}')
for e in data[:5]:
    cam = e['cam_id']
    vt = e['video_url_template']
    sid = e['sourceId']
    print(f'  {cam}: video_url_template={vt} | sourceId={sid}')
print()
# How many need token? How many have token?
have_tok = sum(1 for e in data if e.get('fl_token'))
print(f'Have fl_token: {have_tok}')
print(f'Need token (have template): {sum(1 for e in data if e["video_url_template"] and not e.get("fl_token"))}')
print(f'Need both (no template, have token): {sum(1 for e in data if not e["video_url_template"] and e.get("fl_token"))}')
print(f'Need both (no template, no token): {sum(1 for e in data if not e["video_url_template"] and not e.get("fl_token"))}')
