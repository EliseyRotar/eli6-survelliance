"""Force the 12th shard to load by zooming/panning the map, then capture."""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'
TARGET_SHARD = 'cbfb074892'

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        shard_data = None
        all_shards = {}

        async def on_response(resp):
            nonlocal shard_data
            url = resp.url
            if '/internal/catalog/shards/' in url:
                try:
                    body = await resp.text()
                    sid = url.split('/')[-1].replace('.json', '')
                    all_shards[sid] = body
                    if sid == TARGET_SHARD:
                        shard_data = body
                        print(f'  [CAPTURED] {sid}: {len(body)} bytes', flush=True)
                except Exception as e:
                    pass

        page.on('response', on_response)

        print('[1] Going to trafficvision.live/map...', flush=True)
        try:
            await page.goto('https://trafficvision.live/map', wait_until='domcontentloaded', timeout=90000)
        except Exception as e:
            print(f'  goto err: {e}', flush=True)
        await asyncio.sleep(30)

        # Pan/zoom to trigger different shard loads
        print('[2] Panning map to load all shards...', flush=True)
        # Try clicking the map at different locations
        try:
            map_el = await page.query_selector('.leaflet-container')
            if map_el:
                box = await map_el.bounding_box()
                if box:
                    # Click at various positions to load different areas
                    for x_pct, y_pct in [(0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9), (0.5, 0.5), (0.2, 0.5), (0.8, 0.5)]:
                        await page.mouse.click(box['x'] + box['width']*x_pct, box['y'] + box['height']*y_pct)
                        await asyncio.sleep(2)
        except Exception as e:
            print(f'  pan err: {e}', flush=True)

        # Wait more
        await asyncio.sleep(30)
        print(f'  Captured: {len(all_shards)} shards', flush=True)
        for sid in sorted(all_shards.keys()):
            print(f'    {sid}: {len(all_shards[sid]):,} bytes', flush=True)

        # Save the target shard
        if shard_data:
            out = os.path.join(SHARDS_DIR, f'{TARGET_SHARD}.json')
            with open(out, 'w', encoding='utf-8') as f:
                f.write(shard_data)
            print(f'\n  Saved {TARGET_SHARD} to {out}', flush=True)
        else:
            print(f'\n  Target shard {TARGET_SHARD} NOT captured', flush=True)

        # Build full catalog
        print(f'\n[3] Building full catalog with all shards...', flush=True)
        all_cams = []
        for f in sorted(os.listdir(SHARDS_DIR)):
            if f.endswith('.json') and f != 'manifest.json' and f != 'manifest-e5d25aea.js':
                try:
                    with open(os.path.join(SHARDS_DIR, f), encoding='utf-8') as fh:
                        shard = json.load(fh)
                    if isinstance(shard, dict) and 'cameras' in shard:
                        all_cams.extend(shard['cameras'])
                except:
                    pass
        print(f'  Total cams: {len(all_cams):,}', flush=True)

        # Save
        cat_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
        with open(cat_path, 'w', encoding='utf-8') as f:
            json.dump({'cameras': all_cams, 'fetched': time.time()}, f)
        print(f'  Saved to {cat_path}', flush=True)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
