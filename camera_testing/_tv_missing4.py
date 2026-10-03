"""Try to capture the missing shard by scrolling the SPA and forcing map view."""
import asyncio
import os
import json

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'
os.makedirs(SHARDS_DIR, exist_ok=True)


async def fetch():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        )
        page = await context.new_page()

        captured = {}
        async def cap(response):
            try:
                url = response.url
                if '/catalog/shards/' in url:
                    body = await response.body()
                    if url not in captured:
                        captured[url] = body
                        print(f'Cap: {url.split("/")[-1]} ({len(body)} bytes)')
            except Exception:
                pass
        page.on('response', cap)

        print('Loading map page...')
        await page.goto('https://trafficvision.live/map', timeout=60000, wait_until='networkidle')
        await asyncio.sleep(8)
        print(f'After map: {len(captured)} shards')

        # Scroll the page
        for y in [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000]:
            await page.evaluate(f'window.scrollTo(0, {y})')
            await asyncio.sleep(2)
        print(f'After scroll: {len(captured)} shards')

        # Try home page
        print('Loading home...')
        await page.goto('https://trafficvision.live/', timeout=60000, wait_until='networkidle')
        await asyncio.sleep(5)
        print(f'After home: {len(captured)} shards')

        # Wait longer
        await page.wait_for_timeout(10000)
        print(f'After wait: {len(captured)} shards')

        # Save all unique captured
        for url, body in captured.items():
            name = url.split('/')[-1]
            path = os.path.join(SHARDS_DIR, name)
            with open(path, 'wb') as f:
                f.write(body)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(fetch())
