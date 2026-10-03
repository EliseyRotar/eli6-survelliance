"""Fetch full shard content by going to each URL via the browser."""
import asyncio
import json
import os

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'
CAPTURED = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_captured.json'
OUTPUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
os.makedirs(SHARDS_DIR, exist_ok=True)


async def fetch_full():
    from playwright.async_api import async_playwright

    with open(CAPTURED) as f:
        captured = json.load(f)

    shard_urls = sorted(set(r['url'] for r in captured if '/catalog/shards/' in r['url']))
    manifest_urls = sorted(set(r['url'] for r in captured if '/manifest' in r['url']))
    all_urls = shard_urls + manifest_urls
    print(f'URLs to fetch: {len(all_urls)}')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        )
        page = await context.new_page()
        print('Passing Cloudflare...')
        await page.goto('https://trafficvision.live/', timeout=60000, wait_until='networkidle')
        await asyncio.sleep(3)

        full_cams = []
        for url in all_urls:
            print(f'Fetching {url.split("/")[-1]}...')
            try:
                resp = await page.goto(url, timeout=60000, wait_until='domcontentloaded')
                if not resp:
                    print('  no resp')
                    continue
                if resp.status != 200:
                    print(f'  status {resp.status}')
                    continue
                body = await resp.text()
                name = url.split('/')[-1]
                path = os.path.join(SHARDS_DIR, name)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(body)
                if '/catalog/shards/' in url:
                    try:
                        d = json.loads(body)
                        cams = d.get('cameras', [])
                        full_cams.extend(cams)
                        print(f'  {name}: {len(cams)} cams ({len(body)} bytes)')
                    except Exception as e:
                        print(f'  parse err: {e}')
                else:
                    print(f'  manifest saved ({len(body)} bytes)')
                await asyncio.sleep(1)  # rate limit
            except Exception as e:
                print(f'  err: {e}')

        await browser.close()

    print(f'\nTotal cameras: {len(full_cams)}')
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({'cameras': full_cams}, f, indent=2)
    print(f'Saved to {OUTPUT}')


if __name__ == '__main__':
    asyncio.run(fetch_full())
