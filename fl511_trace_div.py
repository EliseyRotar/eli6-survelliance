"""Trigger Show Video on a cam that has a real divas template.

Use the cam with sourceId 454 (I-95 @ MM 183.3 SB).
"""
import asyncio
import json
import time
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        # Capture all
        events = []
        async def on_request(req):
            try:
                post = req.post_data
            except:
                post = None
            events.append({
                'type': 'request',
                'method': req.method,
                'url': req.url,
                'post_data': post,
                'headers': await req.all_headers(),
            })
        async def on_response(resp):
            try:
                body = await resp.text()
            except:
                body = ''
            events.append({
                'type': 'response',
                'status': resp.status,
                'url': resp.url,
                'body': body[:2000] if body else '',
            })
        page.on('request', on_request)
        page.on('response', on_response)

        # Navigate
        print('Going to fl511.com/cctv...', flush=True)
        try:
            await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=90000)
        except:
            pass
        await asyncio.sleep(30)
        try:
            await page.reload(wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(30)

        # Use the search to find a specific cam
        print('Searching for I-95 cam...', flush=True)
        # First find the search input
        search_input = await page.query_selector('input[type="search"]')
        if search_input:
            await search_input.fill('I-95 @ MM 183.3')
            await asyncio.sleep(3)
            print('Search done', flush=True)
        else:
            # Try other selectors
            search_input = await page.query_selector('input.form-control')
            if search_input:
                await search_input.fill('I-95 @ MM 183.3')
                await asyncio.sleep(3)

        # Find and click first Show Video button (now filtered to our cam)
        events_before = len(events)
        print('Looking for Show Video button...', flush=True)
        for i in range(5):  # Try up to 5 times in case of new cams loading
            buttons = await page.query_selector_all('button')
            print(f'  Found {len(buttons)} buttons', flush=True)
            for b in buttons:
                try:
                    text = await b.text_content()
                    if text and 'show video' in text.lower():
                        print(f'Clicking: {text[:30]}', flush=True)
                        await b.click()
                        await asyncio.sleep(15)  # Let video load
                        break
                except:
                    pass
            else:
                continue
            break

        # Print all events related to divas / m3u8
        print(f'\n=== Total events: {len(events)} ===', flush=True)
        print(f'=== Events after click: {len(events) - events_before} ===', flush=True)

        for e in events:
            url = e.get('url', '')
            if 'divas' in url or 'm3u8' in url or 'GetVideo' in url:
                etype = e['type']
                if etype == 'request':
                    print(f'\n[{e["method"]}] {url[:200]}', flush=True)
                    if e.get('post_data'):
                        print(f'  POST: {e["post_data"][:300]}', flush=True)
                    h = e.get('headers', {})
                    for k, v in h.items():
                        if any(s in k.lower() for s in ['token', 'auth', 'cookie', 'origin', 'referer']):
                            print(f'  {k}: {v[:200]}', flush=True)
                else:
                    print(f'\n[{e["status"]}] {url[:200]}', flush=True)
                    if e.get('body'):
                        print(f'  body: {e["body"][:300]}', flush=True)

        # Save
        with open('fl511_video_div.json', 'w') as f:
            json.dump(events, f, indent=2, default=str)
        print(f'\nSaved {len(events)} events', flush=True)

        await browser.close()

asyncio.run(main())
