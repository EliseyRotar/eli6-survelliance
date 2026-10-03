"""Refresh TV catalog using Playwright session - bypass Cloudflare + auth."""
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

        # First go to home to get session cookies + bypass Cloudflare
        print('[1] Going to trafficvision.live/...', flush=True)
        try:
            await page.goto('https://trafficvision.live/', wait_until='domcontentloaded', timeout=90000)
        except Exception as e:
            print(f'  goto err: {e}', flush=True)
        await asyncio.sleep(20)
        print(f'  URL: {page.url}', flush=True)
        title = await page.title()
        print(f'  Title: {title[:80]}', flush=True)

        # Now try the manifest
        print('\n[2] Fetching manifest via page fetch...', flush=True)
        result = await page.evaluate('''async () => {
            try {
                const r = await fetch('https://api.trafficvision.live/internal/manifest', {
                    credentials: 'include',
                    mode: 'cors',
                });
                return { status: r.status, body: (await r.text()).slice(0, 5000) };
            } catch (e) {
                return { error: e.message };
            }
        }''')
        print(f'  Result: {result}', flush=True)
        if 'error' in result:
            print(f'  CORS error, trying no-cors...', flush=True)
            result = await page.evaluate('''async () => {
                try {
                    const r = await fetch('https://api.trafficvision.live/internal/manifest', {
                        credentials: 'include',
                        mode: 'no-cors',
                    });
                    return { status: r.status, type: r.type };
                } catch (e) {
                    return { error: e.message };
                }
            }''')
            print(f'  No-cors: {result}', flush=True)
            manifest = None
        elif result.get('status') == 200:
            print(f'  Body: {result.get("body", "")[:500]}', flush=True)
            manifest = json.loads(result['body'])
        else:
            print(f'  Status: {result.get("status")}', flush=True)
            print(f'  Body: {result.get("body", "")[:500]}', flush=True)
            manifest = None

        if not manifest:
            await browser.close()
            return

        # Save manifest
        manifest_path = os.path.join(SHARDS_DIR, 'manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        print(f'  Saved to {manifest_path}', flush=True)

        # Get shard list
        if 'shards' in manifest and isinstance(manifest['shards'], list):
            shard_ids = [s.get('id') for s in manifest['shards'] if isinstance(s, dict) and s.get('id')]
        elif 'catalog' in manifest:
            shard_ids = list(manifest.get('catalog', {}).keys())
        else:
            shard_ids = list(manifest.keys())[:20]  # fallback

        print(f'  Shard count: {len(shard_ids)}', flush=True)
        print(f'  First 5: {shard_ids[:5]}', flush=True)

        # Existing
        existing = set()
        for f in os.listdir(SHARDS_DIR):
            if f.endswith('.json') and f != 'manifest.json' and f != 'manifest-e5d25aea.js':
                existing.add(f.replace('.json', ''))
        print(f'  Existing: {len(existing)}', flush=True)
        new_shards = [s for s in shard_ids if s not in existing]
        print(f'  New: {len(new_shards)}', flush=True)

        # Download all shards
        print(f'\n[3] Downloading {len(shard_ids)} shards...', flush=True)
        t0 = time.time()
        for i, sid in enumerate(shard_ids):
            out_path = os.path.join(SHARDS_DIR, f'{sid}.json')
            if os.path.exists(out_path) and (time.time() - os.path.getmtime(out_path)) < 3600:
                continue
            result = await page.evaluate('''async (sid) => {
                const r = await fetch(`https://api.trafficvision.live/internal/catalog/shards/${sid}.json`, {
                    credentials: 'include',
                });
                if (!r.ok) return { error: r.status };
                return { body: await r.text() };
            }''', sid)
            if 'body' in result:
                with open(out_path, 'w') as f:
                    f.write(result['body'])
                size = len(result['body']) / 1024 / 1024
                elapsed = time.time() - t0
                print(f'  [{i+1}/{len(shard_ids)}] {sid}: {size:.1f}MB', flush=True)
            else:
                print(f'  [{i+1}/{len(shard_ids)}] {sid}: err {result.get("error")}', flush=True)
            time.sleep(0.3)

        # Build catalog
        print(f'\n[4] Building full catalog...', flush=True)
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
            except Exception as e:
                print(f'  err reading {sid}: {e}', flush=True)

        print(f'  Total cams: {len(all_cams):,}', flush=True)

        # Save
        cat_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
        with open(cat_path, 'w') as f:
            json.dump({'cameras': all_cams, 'fetched': time.time()}, f)
        print(f'  Saved to {cat_path}', flush=True)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
