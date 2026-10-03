"""Find where fl511.com gets the chan-N from for video playback."""
import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture
        all_data = []
        async def on_request(req):
            if 'divas' in req.url.lower() or 'm3u8' in req.url.lower() or 'GetVideo' in req.url:
                try:
                    body = req.post_data if req.method == 'POST' else None
                    all_data.append({
                        'url': req.url,
                        'method': req.method,
                        'post_data': body,
                        'headers': await req.all_headers(),
                    })
                except:
                    pass
        page.on('request', on_request)

        # Navigate and click
        try:
            await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(30)
        try:
            await page.reload(wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(20)

        # Click multiple Show Video buttons and capture URLs
        buttons = await page.query_selector_all('button')
        for b in buttons[:5]:
            try:
                text = await b.text_content()
                if text and 'show video' in text.lower():
                    all_data.clear()
                    print(f'Clicking: {text[:30]}', flush=True)
                    await b.click()
                    await asyncio.sleep(8)
                    for d in all_data:
                        print(f'  [{d["method"]}] {d["url"]}', flush=True)
                        if d.get('post_data'):
                            print(f'    POST: {d["post_data"][:200]}', flush=True)
                    break
            except:
                pass

        await browser.close()

asyncio.run(main())
