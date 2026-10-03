"""Capture the missing shard cbfb074892.json."""
import asyncio
import os

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'
OUTPUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
os.makedirs(SHARDS_DIR, exist_ok=True)


async def fetch():
    from playwright.async_api import async_playwright

    url = 'https://api.trafficvision.live/internal/catalog/shards/cbfb074892.json'
    print(f'Fetching {url}...')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        )
        page = await context.new_page()
        # Clear CF
        await page.goto('https://trafficvision.live/', timeout=60000, wait_until='networkidle')
        await asyncio.sleep(3)

        captured = {}
        async def cap(response):
            try:
                if '/catalog/shards/' in response.url:
                    body = await response.body()
                    captured[response.url] = body
                    print(f'Captured: {response.url.split("/")[-1]} ({len(body)} bytes)')
            except Exception:
                pass
        page.on('response', cap)
        # Now trigger fetch via JS injection
        result = await page.evaluate(f'''
            async () => {{
                try {{
                    const r = await fetch('{url}', {{ credentials: 'include' }});
                    const t = await r.text();
                    return {{ ok: r.ok, status: r.status, len: t.length, body: t }};
                }} catch (e) {{
                    return {{ ok: false, err: String(e) }};
                }}
            }}
        ''')
        print('Result:', result.get('ok'), result.get('status'), result.get('len', 0))

        if result.get('ok') and result.get('status') == 200:
            path = os.path.join(SHARDS_DIR, 'cbfb074892.json')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(result['body'])
            print(f'Saved {len(result["body"])} bytes to {path}')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(fetch())
