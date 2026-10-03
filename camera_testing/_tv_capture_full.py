"""Use Playwright to navigate to trafficvision.live and capture full shard responses."""
import asyncio
import json
import os
import re

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'
OUTPUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
os.makedirs(SHARDS_DIR, exist_ok=True)


async def capture_full():
    from playwright.async_api import async_playwright

    captured = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        )
        page = await context.new_page()

        # Capture all responses, especially shards
        async def capture(response):
            try:
                url = response.url
                if '/catalog/shards/' in url or '/manifest' in url:
                    body = await response.body()
                    captured[url] = body
                    print(f'Captured: {url.split("/")[-1]} ({len(body)} bytes)')
            except Exception:
                pass
        page.on('response', capture)

        # Navigate to home (triggers SPA load which fetches catalog)
        print('Loading homepage...')
        await page.goto('https://trafficvision.live/', timeout=60000, wait_until='networkidle')
        # Wait for all shards to load
        print('Waiting for catalog shards to load...')
        await page.wait_for_timeout(20000)

        # Check if we got them all
        print(f'\nTotal captured: {len(captured)}')
        total_bytes = sum(len(b) for b in captured.values())
        print(f'Total bytes: {total_bytes:,}')

        await browser.close()

    # Save full content
    full_cams = []
    for url, body in captured.items():
        name = url.split('/')[-1]
        path = os.path.join(SHARDS_DIR, name)
        with open(path, 'wb') as f:
            f.write(body)
        if '/catalog/shards/' in url:
            try:
                d = json.loads(body.decode('utf-8', errors='replace'))
                cams = d.get('cameras', [])
                full_cams.extend(cams)
                print(f'  {name}: {len(cams)} cams')
            except Exception as e:
                print(f'  parse err {name}: {e}')

    print(f'\nTotal cameras: {len(full_cams)}')
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({'cameras': full_cams}, f, indent=2)
    print(f'Saved to {OUTPUT}')


if __name__ == '__main__':
    asyncio.run(capture_full())
