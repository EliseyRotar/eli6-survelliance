"""Inspect how fl511 video URL is used."""
import asyncio
import json
import time
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture all
        all_data = []
        async def on_response(resp):
            url = resp.url
            if '/Camera/GetVideoUrl' in url or 'divas' in url.lower() or 'm3u8' in url.lower() or 'token' in url.lower():
                try:
                    body = await resp.text()
                    req_headers = {}
                    try:
                        req_headers = await resp.request.all_headers() if resp.request else {}
                    except:
                        pass
                    all_data.append({
                        'url': url,
                        'status': resp.status,
                        'request_headers': req_headers,
                        'response_headers': dict(resp.headers),
                        'body': body[:1500],
                    })
                except Exception as e:
                    all_data.append({'url': url, 'err': str(e)})
        page.on('response', on_response)

        print('[1] Going to fl511.com/cctv...', flush=True)
        try:
            await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(f'  goto err: {e}', flush=True)
        await asyncio.sleep(30)
        try:
            await page.reload(wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(f'  reload err: {e}', flush=True)
        await asyncio.sleep(20)

        # Click Show Video button
        try:
            buttons = await page.query_selector_all('button')
            for b in buttons:
                text = await b.text_content()
                if text and 'show video' in text.lower():
                    print(f'Clicking: {text[:30]}', flush=True)
                    await b.click()
                    await asyncio.sleep(15)
                    break
        except Exception as e:
            print(f'Click err: {e}', flush=True)

        print(f'\n[2] Captured {len(all_data)} responses', flush=True)
        for d in all_data:
            url = d.get('url', '?')
            status = d.get('status')
            print(f'\n=== {url[:200]} ===', flush=True)
            print(f'  Status: {status}', flush=True)
            body = d.get('body', '')
            if body:
                print(f'  Body: {body[:600]}', flush=True)
            # Show key headers
            rh = d.get('request_headers', {})
            for k in ['authorization', '__requestverificationtoken', 'x-requested-with']:
                if k in rh:
                    print(f'  Req {k}: {str(rh[k])[:100]}', flush=True)

        # Save
        with open('fl511_video_url_flow.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        print(f'\nSaved to fl511_video_url_flow.json', flush=True)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
