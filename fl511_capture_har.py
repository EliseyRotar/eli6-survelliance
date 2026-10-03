"""Save full HAR-like trace of fl511 live video flow to find the divas auth.

Captures all requests including body, headers, and timing.
"""
import asyncio
import json
import time
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(record_video_dir=None, record_har_path='fl511_full_trace.har')
        page = await ctx.new_page()

        # Capture all requests with full detail
        all_requests = []

        async def on_request(req):
            try:
                post = None
                try:
                    post = req.post_data
                except:
                    pass
                req_data = {
                    'url': req.url,
                    'method': req.method,
                    'headers': await req.all_headers(),
                    'post_data': post,
                    'resource_type': req.resource_type,
                }
                all_requests.append(req_data)
            except Exception as e:
                pass
        page.on('request', on_request)

        async def on_response(resp):
            try:
                req_data = {
                    'url': resp.url,
                    'status': resp.status,
                    'headers': dict(resp.headers),
                }
                all_requests.append({'response': req_data})
            except:
                pass
        page.on('response', on_response)

        # Navigate
        print('Going to fl511.com/cctv...', flush=True)
        try:
            await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=90000)
        except:
            pass
        await asyncio.sleep(30)

        # Find and click the first "Show Video" button
        print('Looking for Show Video button...', flush=True)
        try:
            await page.reload(wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(20)

        # Find first Show Video button
        clicked = False
        buttons = await page.query_selector_all('button')
        for b in buttons:
            try:
                text = await b.text_content()
                if text and 'show video' in text.lower():
                    print(f'Clicking: {text[:30]}', flush=True)
                    # Get cam info from data
                    parent = await b.evaluate_handle('e => e.closest("tr") || e.closest("td") || e.closest("div")')
                    await b.click()
                    clicked = True
                    break
            except:
                pass

        if not clicked:
            print('No Show Video button found', flush=True)
        await asyncio.sleep(15)  # Let video load

        # Save all requests
        with open('fl511_full_trace.json', 'w') as f:
            json.dump(all_requests, f, indent=2, default=str)
        print(f'\nSaved {len(all_requests):,} events to fl511_full_trace.json', flush=True)

        # Also save HAR
        await ctx.close()
        print('Saved HAR', flush=True)

        # Print interesting ones
        print('\n=== DIVAS REQUESTS ===', flush=True)
        for r in all_requests:
            if 'divas.cloud' in str(r.get('url', '')):
                print(json.dumps(r, indent=2, default=str)[:2000], flush=True)

        await browser.close()

asyncio.run(main())
