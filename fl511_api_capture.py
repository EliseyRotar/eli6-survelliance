"""Get the actual API request from the page using Playwright."""
import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture all
        all_data = []
        async def on_response(resp):
            if '/List/GetData/Cameras' in resp.url:
                try:
                    body = await resp.text()
                    all_data.append({
                        'url': resp.url,
                        'status': resp.status,
                        'request_headers': await resp.request.all_headers() if resp.request else {},
                        'response_headers': resp.headers,
                        'body': body[:500],
                    })
                except Exception as e:
                    all_data.append({'url': resp.url, 'err': str(e)})
        page.on('response', on_response)

        # Navigate
        print('[1] Navigating...', flush=True)
        try:
            await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(60)
        # Reload to trigger AJAX
        print('[2] Reload to trigger AJAX...', flush=True)
        try:
            await page.reload(wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(20)

        # Save
        with open('fl511_api_request.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        print(f'\nCaptured {len(all_data)} /List/GetData/Cameras responses', flush=True)
        for d in all_data:
            print(f'\n=== {d.get("url", "?")} ===', flush=True)
            print(f'Status: {d.get("status")}', flush=True)
            if 'request_headers' in d:
                for k, v in d['request_headers'].items():
                    if k.lower() in ['cookie', 'x-requested-with', 'accept', 'referer', 'user-agent', 'content-type', '__requestverificationtoken', 'authorization']:
                        print(f'  Req Header: {k}: {str(v)[:200]}', flush=True)
            if 'body' in d and d['body']:
                print(f'Body: {d["body"][:1500]}', flush=True)

        await browser.close()

asyncio.run(main())
