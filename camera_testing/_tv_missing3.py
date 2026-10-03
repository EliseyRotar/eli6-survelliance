"""Capture missing shard by triggering fetch from within the SPA context."""
import asyncio
import os
import json

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'
OUTPUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
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
                if '/catalog/shards/' in url or '/manifest' in url:
                    body = await response.body()
                    captured[url] = body
                    print(f'Cap: {url.split("/")[-1]} ({len(body)} bytes)')
            except Exception:
                pass
        page.on('response', cap)

        print('Loading SPA...')
        await page.goto('https://trafficvision.live/', timeout=60000, wait_until='networkidle')
        await asyncio.sleep(5)

        # Wait for shards to all load
        # Then navigate around to trigger missing shard
        # Or scroll to trigger lazy load
        print(f'Captured so far: {len(captured)}')

        # Force fetch the missing shard by injecting script that uses SPA's session
        result = await page.evaluate('''
            async () => {
                // Try to use the SPA's existing session by calling fetch with same credentials
                try {
                    const r = await fetch('https://api.trafficvision.live/internal/catalog/shards/cbfb074892.json', {
                        credentials: 'include',
                    });
                    if (!r.ok) return { ok: false, status: r.status, text: await r.text() };
                    const t = await r.text();
                    return { ok: true, status: r.status, len: t.length, body: t };
                } catch (e) {
                    return { ok: false, err: String(e) };
                }
            }
        ''')
        print(f'Result: {result.get("ok")} status={result.get("status")} len={result.get("len", 0)} err={result.get("err", "")}')

        if result.get('ok'):
            path = os.path.join(SHARDS_DIR, 'cbfb074892.json')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(result['body'])
            d = json.loads(result['body'])
            print(f'Saved: {len(d.get("cameras", []))} cams')

        # Also try the manifest endpoint which lists all shards
        m_result = await page.evaluate('''
            async () => {
                try {
                    const r = await fetch('https://api.trafficvision.live/internal/manifest', {
                        credentials: 'include',
                    });
                    if (!r.ok) return { ok: false, status: r.status };
                    return { ok: true, status: r.status, body: await r.text() };
                } catch (e) {
                    return { ok: false, err: String(e) };
                }
            }
        ''')
        if m_result.get('ok'):
            print(f'Manifest: {len(m_result["body"])} bytes')
            with open(os.path.join(SHARDS_DIR, 'manifest2.json'), 'w', encoding='utf-8') as f:
                f.write(m_result['body'])

        await browser.close()


if __name__ == '__main__':
    asyncio.run(fetch())
