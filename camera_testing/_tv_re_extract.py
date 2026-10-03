"""Re-extract full catalog from saved shards (handle non-UTF8 bytes)."""
import json
import os

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'
OUTPUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'

all_cameras = []
for f in sorted(os.listdir(SHARDS_DIR)):
    if not f.endswith('.json') or f == 'manifest.json' or f == 'manifest2.json':
        continue
    path = os.path.join(SHARDS_DIR, f)
    try:
        with open(path, 'rb') as ff:
            raw = ff.read()
        # Try UTF-8 first, then UTF-16, then latin-1
        text = None
        for enc in ['utf-8', 'utf-16', 'utf-8-sig', 'cp1252', 'latin-1']:
            try:
                text = raw.decode(enc)
                # Validate it's JSON
                json.loads(text)
                break
            except Exception:
                continue
        if text is None:
            # Force decode with replacement
            text = raw.decode('utf-8', errors='replace')
        d = json.loads(text)
        cams = d.get('cameras', [])
        all_cameras.extend(cams)
        print(f'  {f}: {len(cams)} cams')
    except Exception as e:
        print(f'  err {f}: {e}')

print(f'\nTOTAL: {len(all_cameras)}')
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump({'cameras': all_cameras}, f, indent=2)
print(f'Saved {OUTPUT}')
