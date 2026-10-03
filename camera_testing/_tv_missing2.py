"""Capture missing shard cbfb074892.json via page.goto."""
import asyncio
import os
import json

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'
OUTPUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
os.makedirs(SHARDS_DIR, exist_ok=True)


async def fetch():
    from playwright.async_api import async_playwright

    url = 'https://api.trafficvision.live/internal/catalog/shards/cbfb074892.json'

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        )
        page = await context.new_page()
        print('Passing CF...')
        await page.goto('https://trafficvision.live/', timeout=60000, wait_until='networkidle')
        await asyncio.sleep(3)

        # Now navigate directly to the shard URL
        print(f'Going to {url}')
        try:
            resp = await page.goto(url, timeout=60000, wait_until='domcontentloaded')
            if not resp:
                print('No response')
            else:
                print(f'Status: {resp.status}')
                if resp.status == 200:
                    body = await resp.text()
                    print(f'Got {len(body)} bytes')
                    path = os.path.join(SHARDS_DIR, 'cbfb074892.json')
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(body)
                    print(f'Saved to {path}')
                    try:
                        d = json.loads(body)
                        print(f'Cams in shard: {len(d.get("cameras", []))}')
                    except Exception as e:
                        print(f'Parse err: {e}')
                else:
                    body = await resp.text()
                    print(f'Body: {body[:200]}')
        except Exception as e:
            print(f'err: {e}')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(fetch())
