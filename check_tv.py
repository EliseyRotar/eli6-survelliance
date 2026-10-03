"""Check TV catalog structure."""
import json
import os

PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
print(f'Size: {os.path.getsize(PATH)/1024/1024:.1f} MB')

with open(PATH, 'r') as f:
    catalog = json.load(f)
print(f'Type: {type(catalog).__name__}')
if isinstance(catalog, list):
    print(f'Cams: {len(catalog):,}')
    if catalog:
        c0 = catalog[0]
        print(f'First keys: {list(c0.keys())}')
        # Show sample fields
        for k, v in c0.items():
            vstr = str(v)[:80]
            print(f'  {k}: {vstr}')
elif isinstance(catalog, dict):
    print(f'Keys: {list(catalog.keys())[:20]}')
    cams = catalog.get('cameras', [])
    print(f'cameras: {len(cams):,}')
    if cams:
        c0 = cams[0]
        print(f'First cam keys: {list(c0.keys())}')
        for k, v in c0.items():
            vstr = str(v)[:80]
            print(f'  {k}: {vstr}')
