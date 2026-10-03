"""Refresh TV catalog using browser session + capture all 12 shards."""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        # Track downloaded shards
        downloaded = {}
        new_session = {}

        async def on_response(resp):
            url = resp.url
            if '/internal/manifest' in url and 'manifest.json' not in url:
                try:
                    body = await resp.text()
                    with open(os.path.join(SHARDS_DIR, 'manifest.json'), 'w', encoding='utf-8') as f:
                        f.write(body)
                    print(f'  Manifest: {len(body)} bytes', flush=True)
                except Exception as e:
                    print(f'  Manifest err: {e}', flush=True)
            elif '/internal/catalog/shards/' in url:
                # Extract shard ID
                sid = url.split('/')[-1].replace('.json', '')
                try:
                    body = await resp.text()
                    with open(os.path.join(SHARDS_DIR, f'{sid}.json'), 'w', encoding='utf-8') as f:
                        f.write(body)
                    downloaded[sid] = len(body)
                except Exception as e:
                    pass
            elif '/api/session' in url:
                try:
                    body = await resp.text()
                    new_session = json.loads(body)
                except:
                    pass

        page.on('response', on_response)

        # Navigate
        print('[1] Going to trafficvision.live/map...', flush=True)
        try:
            await page.goto('https://trafficvision.live/map', wait_until='domcontentloaded', timeout=90000)
        except Exception as e:
            print(f'  goto err: {e}', flush=True)
        await asyncio.sleep(60)
        print(f'  URL: {page.url}', flush=True)

        print(f'\n[2] Downloaded: {len(downloaded)} shards, total {sum(downloaded.values())/1024/1024:.1f}MB', flush=True)
        for sid, size in sorted(downloaded.items()):
            print(f'  {sid}: {size/1024/1024:.1f}MB', flush=True)

        # Get the manifest
        manifest_path = os.path.join(SHARDS_DIR, 'manifest.json')
        if not os.path.exists(manifest_path):
            print('  No manifest downloaded, trying direct fetch', flush=True)
            # Use the browser to get the manifest URL
            manifest = await page.evaluate('''async () => {
                try {
                    const r = await fetch('/internal/manifest', {credentials: 'include'});
                    if (!r.ok) return null;
                    return await r.json();
                } catch (e) { return {error: e.message}; }
            }''')
            if manifest and 'shards' in manifest:
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2)
                print(f'  Saved manifest: {len(manifest.get("shards", []))} shards, {manifest.get("totalCameras")} total cams', flush=True)

        # Build catalog
        print(f'\n[3] Building full catalog from shards...', flush=True)
        all_cams = []
        for f in sorted(os.listdir(SHARDS_DIR)):
            if f.endswith('.json') and f != 'manifest.json' and f != 'manifest-e5d25aea.js':
                sid = f.replace('.json', '')
                if sid not in downloaded:
                    continue  # Skip old shards we didn't update
                try:
                    with open(os.path.join(SHARDS_DIR, f), encoding='utf-8') as fh:
                        shard = json.load(fh)
                    if isinstance(shard, list):
                        all_cams.extend(shard)
                    elif isinstance(shard, dict) and 'cameras' in shard:
                        all_cams.extend(shard['cameras'])
                except Exception as e:
                    print(f'  err reading {sid}: {e}', flush=True)
        print(f'  Total cams: {len(all_cams):,}', flush=True)

        # Also load all existing shards (even old ones) for full coverage
        all_cams_full = []
        for f in sorted(os.listdir(SHARDS_DIR)):
            if f.endswith('.json') and f != 'manifest.json' and f != 'manifest-e5d25aea.js':
                try:
                    with open(os.path.join(SHARDS_DIR, f), encoding='utf-8') as fh:
                        shard = json.load(fh)
                    if isinstance(shard, list):
                        all_cams_full.extend(shard)
                    elif isinstance(shard, dict) and 'cameras' in shard:
                        all_cams_full.extend(shard['cameras'])
                except:
                    pass
        print(f'  Total cams (all shards incl old): {len(all_cams_full):,}', flush=True)

        # Save the new full catalog
        cat_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
        with open(cat_path, 'w', encoding='utf-8') as f:
            json.dump({'cameras': all_cams_full, 'fetched': time.time()}, f)
        print(f'  Saved to {cat_path}', flush=True)

        # Get the version
        try:
            with open(manifest_path) as f:
                m = json.load(f)
            print(f'\n  Manifest version: {m.get("version")}', flush=True)
            print(f'  Manifest totalCameras: {m.get("totalCameras")}', flush=True)
        except:
            pass

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
