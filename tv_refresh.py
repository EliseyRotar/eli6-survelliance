"""Refresh TV catalog manifest + shards."""
import json
import urllib.request
import ssl
import time
import os
import glob

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'


def fetch(url, timeout=30, headers=None):
    try:
        h = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://trafficvision.live/',
        }
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception as e:
        return -1, str(e).encode()


# Load auth
with open('camera_testing/tv_auth.json') as f:
    auth = json.load(f)
id_token = auth.get('idToken', '')

# Get manifest
print('[1] Fetching manifest...', flush=True)
for auth_scheme in [None, f'Bearer {id_token}', f'Firebase {id_token}']:
    headers = {}
    if auth_scheme:
        headers['Authorization'] = auth_scheme
    status, body = fetch('https://api.trafficvision.live/internal/manifest', headers=headers)
    print(f'  With {auth_scheme or "no auth"}: {status}', flush=True)
    if status == 200:
        break
if status == 200:
    manifest = json.loads(body)
    print(f'  Manifest keys: {list(manifest.keys())}', flush=True)
    # Save
    manifest_path = os.path.join(SHARDS_DIR, 'manifest.json')
    with open(manifest_path, 'wb') as f:
        f.write(body)
    print(f'  Saved to {manifest_path}', flush=True)

    # List shard IDs
    if 'shards' in manifest:
        shard_ids = [s.get('id') for s in manifest['shards'] if isinstance(s, dict) and s.get('id')]
    elif 'catalog' in manifest:
        shard_ids = list(manifest.get('catalog', {}).keys())
    else:
        # Try direct
        shard_ids = list(manifest.keys())

    print(f'  Shard count: {len(shard_ids)}', flush=True)
    print(f'  First 5: {shard_ids[:5]}', flush=True)

    # Check which we have
    existing = set()
    for f in os.listdir(SHARDS_DIR):
        if f.endswith('.json') and f != 'manifest.json' and f != 'manifest-e5d25aea.js':
            existing.add(f.replace('.json', ''))
    print(f'  Existing: {len(existing)}', flush=True)

    new_shards = [s for s in shard_ids if s not in existing]
    print(f'  New shards: {len(new_shards)}', flush=True)

    # Download all shards (new + existing)
    print(f'\n[2] Downloading all {len(shard_ids)} shards...', flush=True)
    t0 = time.time()
    for i, sid in enumerate(shard_ids):
        out_path = os.path.join(SHARDS_DIR, f'{sid}.json')
        # Skip if recent (< 1 hour old)
        if os.path.exists(out_path) and (time.time() - os.path.getmtime(out_path)) < 3600:
            continue
        url = f'https://api.trafficvision.live/internal/catalog/shards/{sid}.json'
        status, body = fetch(url)
        if status == 200:
            with open(out_path, 'wb') as f:
                f.write(body)
            elapsed = time.time() - t0
            rate = (i + 1) / max(elapsed, 1)
            print(f'  [{i+1}/{len(shard_ids)}] {sid}: {len(body)/1024/1024:.1f}MB ({rate:.1f}/s)', flush=True)
        else:
            print(f'  [{i+1}/{len(shard_ids)}] {sid}: err {status}', flush=True)
        time.sleep(0.3)

    # Build full catalog
    print(f'\n[3] Building full catalog from shards...', flush=True)
    all_cams = []
    for sid in shard_ids:
        shard_path = os.path.join(SHARDS_DIR, f'{sid}.json')
        if not os.path.exists(shard_path):
            continue
        try:
            with open(shard_path) as f:
                shard = json.load(f)
            if isinstance(shard, list):
                all_cams.extend(shard)
            elif isinstance(shard, dict) and 'cameras' in shard:
                all_cams.extend(shard['cameras'])
            elif isinstance(shard, dict):
                all_cams.extend(shard.values() if all(isinstance(v, dict) for v in shard.values()) else [])
        except Exception as e:
            print(f'  err reading {sid}: {e}', flush=True)

    print(f'  Total cams: {len(all_cams):,}', flush=True)

    # Save
    cat_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
    with open(cat_path, 'w') as f:
        json.dump({'cameras': all_cams, 'fetched': time.time()}, f)
    print(f'  Saved to {cat_path}', flush=True)
else:
    print(f'  Manifest err: {status}', flush=True)
