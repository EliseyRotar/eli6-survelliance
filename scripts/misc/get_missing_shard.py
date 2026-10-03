"""Download the missing cbfb074892 shard via Playwright session."""
import asyncio
import os
import json
from playwright.async_api import async_playwright

SHARD = 'cbfb074892'
SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        shard_data = None

        async def on_response(resp):
            global shard_data
            url = resp.url
            if f'/shards/{SHARD}.json' in url:
                try:
                    body = await resp.text()
                    shard_data = body
                    print(f'  Got shard! {len(body)} bytes', flush=True)
                except Exception as e:
                    print(f'  Err: {e}', flush=True)

        page.on('response', on_response)

        print('[1] Going to trafficvision.live/map...', flush=True)
        try:
            await page.goto('https://trafficvision.live/map', wait_until='domcontentloaded', timeout=90000)
        except Exception as e:
            print(f'  goto err: {e}', flush=True)
        await asyncio.sleep(45)

        # Try to navigate to a URL that would trigger loading that specific shard
        # The shards are loaded based on visible map area
        print(f'\n[2] Try to load shard {SHARD}...', flush=True)
        # Click on a different region to trigger different shard load
        # Or wait longer
        await asyncio.sleep(30)

        # Try direct API call as a fetch from page
        result = await page.evaluate('''async (sid) => {
            try {
                const r = await fetch(`/internal/catalog/shards/${sid}.json`, {
                    credentials: 'include',
                });
                return { status: r.status, body: (await r.text()).slice(0, 200) };
            } catch (e) {
                return { error: e.message };
            }
        }''', SHARD)
        print(f'  Fetch result: {result}', flush=True)

        if shard_data:
            out = os.path.join(SHARDS_DIR, f'{SHARD}.json')
            with open(out, 'w', encoding='utf-8') as f:
                f.write(shard_data)
            print(f'  Saved to {out}', flush=True)
        elif result.get('status') == 200:
            out = os.path.join(SHARDS_DIR, f'{SHARD}.json')
            with open(out, 'w', encoding='utf-8') as f:
                f.write(result['body'])
            print(f'  Saved via fetch to {out}', flush=True)

        # Build full catalog
        print(f'\n[3] Building full catalog with all 12 shards...', flush=True)
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
            json.dump({'cameras': all_cams, 'fetched': __import__('time').time()}, f)
        print(f'  Saved to {cat_path}', flush=True)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
