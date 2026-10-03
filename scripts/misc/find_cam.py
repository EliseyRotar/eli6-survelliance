"""Find specific cams."""
import json

with open('fl511_cams_all.json') as f:
    data = json.load(f)
# Find imageId 615 and 616
for c in data.get('cams', []):
    if c.get('id') in (615, 616, 617, 614):
        cid = c['id']
        print(f'=== Cam {cid} ===')
        print(json.dumps(c, indent=2)[:3000])
        print()
