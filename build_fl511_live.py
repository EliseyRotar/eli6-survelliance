"""Build fl511 cams data with live URLs.

Reads fl511_cams_all.json, extracts:
- For cams with direct videoUrl: store as live_url
- For cams without: use fl511_live_progress.json (which has tokens)

Output: fl511_cams_with_live.json with all 4,871 cams
"""
import json
import os
import re
from collections import Counter

with open('fl511_cams_all.json', encoding='utf-8') as f:
    all_cams_data = json.load(f)
cams = all_cams_data.get('cams', [])

# Load progress
live_progress = {}
if os.path.exists('fl511_live_progress.json'):
    with open('fl511_live_progress.json', encoding='utf-8') as f:
        p = json.load(f)
    live_progress = p.get('queried', {})

# Build enriched list
enriched = []
n_with_url = 0
n_without = 0
n_no_data = 0
for c in cams:
    images = c.get('images') or []
    if not images:
        continue
    img = images[0]
    cam_id = c.get('id')
    image_id = img.get('id')
    video_url = img.get('videoUrl', '')

    # If we have a token in progress, use it
    fl_token = None
    source_id = c.get('sourceId', '')
    if str(image_id) in live_progress:
        result = live_progress[str(image_id)].get('result', {})
        fl_token = result.get('token', '')

    if video_url:
        # Direct URL - just need to add the token
        n_with_url += 1
        enriched.append({
            'cam_id': cam_id,
            'image_id': image_id,
            'sourceId': source_id,
            'location': c.get('location', ''),
            'roadway': c.get('roadway', ''),
            'direction': c.get('direction', ''),
            'county': c.get('county', ''),
            'region': c.get('region', ''),
            'state': c.get('state', 'Florida'),
            'description': img.get('description', ''),
            'video_url_template': video_url,  # Has chan-N and server but no token
            'has_token': fl_token is not None,
            'fl_token': fl_token,
            'source': c.get('source', ''),
            'lat': c.get('latLng', {}).get('geography', {}).get('wellKnownText', ''),
            'imageUrl': img.get('imageUrl', ''),
        })
    else:
        n_without += 1
        if fl_token:
            # Has fl511 token, need to POST to divas for the secure token
            # We need to figure out chan-N somehow
            enriched.append({
                'cam_id': cam_id,
                'image_id': image_id,
                'sourceId': source_id,
                'location': c.get('location', ''),
                'roadway': c.get('roadway', ''),
                'direction': c.get('direction', ''),
                'county': c.get('county', ''),
                'region': c.get('region', ''),
                'state': c.get('state', 'Florida'),
                'description': img.get('description', ''),
                'video_url_template': '',  # Need to construct
                'has_token': False,
                'fl_token': fl_token,
                'source': c.get('source', ''),
                'lat': c.get('latLng', {}).get('geography', {}).get('wellKnownText', ''),
                'imageUrl': img.get('imageUrl', ''),
            })

print(f'Cams with direct videoUrl: {n_with_url:,}')
print(f'Cams without videoUrl: {n_without:,}')

# Sample URLs
print('\nSample videoUrl templates:')
for e in enriched[:5]:
    print(f'  {e["cam_id"]}: {e["video_url_template"]}')

# Save
with open('fl511_cams_with_live.json', 'w', encoding='utf-8') as f:
    json.dump(enriched, f, indent=2, ensure_ascii=False)
print(f'\nSaved {len(enriched):,} cams to fl511_cams_with_live.json')
