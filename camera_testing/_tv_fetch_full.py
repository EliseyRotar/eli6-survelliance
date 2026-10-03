"""Use Playwright to fetch full shard content (not truncated)."""
import asyncio
import json
import os
import re

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'
CAPTURED = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_captured.json'
OUTPUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
os.makedirs(SHARDS_DIR, exist_ok=True)


async def fetch_full():
    from playwright.async_api import async_playwright

    with open(CAPTURED) as f:
        captured = json.load(f)

    # Extract unique shard URLs
    shard_urls = sorted(set(r['url'] for r in captured if '/catalog/shards/' in r['url']))
    manifest_urls = sorted(set(r['url'] for r in captured if '/manifest' in r['url']))
    print(f'shards to fetch: {len(shard_urls)}')
    print(f'manifests: {len(manifest_urls)}')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        )
        # Need to clear Cloudflare first by visiting homepage
        page = await context.new_page()
        print('Passing Cloudflare...')
        await page.goto('https://trafficvision.live/', timeout=60000, wait_until='networkidle')
        await asyncio.sleep(3)

        # Fetch all shards in parallel using page.evaluate fetch()
        print('Fetching shards via page context...')
        all_results = []
        sem = asyncio.Semaphore(8)

        async def fetch_one(url):
            async with sem:
                try:
                    resp = await page.evaluate(f'''
                        async () => {{
                            const r = await fetch('{url}', {{ credentials: 'include' }});
                            const t = await r.text();
                            return {{ ok: true, status: r.status, body: t }};
                        }}
                    ''')
                    return {'url': url, **resp}
                except Exception as e:
                    return {'url': url, 'ok': False, 'err': str(e)}

        tasks = []
        for url in shard_urls + manifest_urls:
            tasks.append(fetch_one(url))
        results = await asyncio.gather(*tasks)
        all_results.extend(results)

        await browser.close()

    # Save results
    full_cams = []
    for r in all_results:
        url = r['url']
        if not r.get('ok'):
            print(f'FAIL {url}: {r.get("err", "?")}')
            continue
        if r.get('status') != 200:
            print(f'STATUS {r["status"]} {url}')
            continue
        body = r['body']
        # Save to file
        name = url.split('/')[-1]
        path = os.path.join(SHARDS_DIR, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(body)
        # Parse cameras
        if '/catalog/shards/' in url:
            try:
                d = json.loads(body)
                cams = d.get('cameras', [])
                full_cams.extend(cams)
                print(f'  {name}: {len(cams)} cams ({len(body)} bytes)')
            except Exception as e:
                print(f'  parse err {name}: {e}')

    print(f'\nTotal cameras: {len(full_cams)}')
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({'cameras': full_cams}, f, indent=2)
    print(f'Saved to {OUTPUT}')


if __name__ == '__main__':
    asyncio.run(fetch_full())
