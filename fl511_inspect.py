"""Inspect fl511.com network traffic to find live stream URLs."""
import asyncio
import json
import re
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture all network requests
        requests = []
        def on_request(req):
            requests.append({
                'url': req.url,
                'method': req.method,
                'resource_type': req.resource_type,
            })

        page.on('request', on_request)

        # Capture responses too
        responses = []
        async def on_response(resp):
            try:
                body = await resp.body()
                body_str = body[:500].decode('utf-8', errors='replace') if body else ''
            except:
                body_str = ''
            responses.append({
                'url': resp.url,
                'status': resp.status,
                'content_type': resp.headers.get('content-type', ''),
                'body_preview': body_str,
            })
        page.on('response', on_response)

        # Navigate
        print('[1] Navigating to fl511.com/cctv...', flush=True)
        try:
            await page.goto('https://fl511.com/cctv', wait_until='networkidle', timeout=90000)
        except Exception as e:
            print(f'  goto err (continuing): {e}', flush=True)
        await asyncio.sleep(60)  # Let JS SPA fully load

        # Try to find the video element
        video_info = await page.evaluate('''() => {
            const vids = Array.from(document.querySelectorAll('video'));
            return vids.map(v => ({
                src: v.src || '',
                currentSrc: v.currentSrc || '',
                sources: Array.from(v.querySelectorAll('source')).map(s => s.src),
                autoplay: v.autoplay,
                paused: v.paused,
                readyState: v.readyState,
            }));
        }''')
        print(f'\n[Video elements]: {len(video_info)}', flush=True)
        for v in video_info:
            print(json.dumps(v, indent=2), flush=True)

        # Click "Show Video" button
        try:
            buttons = await page.query_selector_all('button')
            print(f'Found {len(buttons)} buttons', flush=True)
            for b in buttons:
                text = await b.text_content()
                if text and 'show video' in text.lower():
                    print(f'Clicking: {text[:50]}', flush=True)
                    await b.click()
                    await asyncio.sleep(10)
                    break
        except Exception as e:
            print(f'Err: {e}', flush=True)

        # After clicking, check video again
        video_info2 = await page.evaluate('''() => {
            const vids = Array.from(document.querySelectorAll('video'));
            return vids.map(v => ({
                src: v.src || '',
                currentSrc: v.currentSrc || '',
                sources: Array.from(v.querySelectorAll('source')).map(s => s.src),
            }));
        }''')
        print(f'\n[Video after click]: {video_info2}', flush=True)

        # Print all captured requests/responses
        print(f'\n=== NETWORK REQUESTS ({len(requests)}) ===', flush=True)
        seen = set()
        for r in requests:
            if r['url'] not in seen:
                seen.add(r['url'])
                if 'fl511' in r['url'] or 'cctv' in r['url'].lower() or 'cam' in r['url'].lower() or 'video' in r['url'].lower() or 'stream' in r['url'].lower() or 'divas' in r['url'].lower() or 'm3u8' in r['url']:
                    print(f"  [{r['method']}] {r['resource_type']:8s} {r['url'][:200]}", flush=True)

        print(f'\n=== NETWORK RESPONSES ({len(responses)}) ===', flush=True)
        seen = set()
        for r in responses:
            if r['url'] not in seen:
                seen.add(r['url'])
                if 'fl511' in r['url'] or 'cctv' in r['url'].lower() or 'cam' in r['url'].lower() or 'm3u8' in r['url'] or 'mjpg' in r['url'] or 'divas' in r['url'].lower() or 'GetVideoUrl' in r['url']:
                    body = r['body_preview'].replace('\n', ' ')
                    print(f"  [{r['status']}] {r['content_type'][:30]:30s} {r['url'][:200]}", flush=True)
                    if body and len(body) > 5:
                        print(f"      body: {body[:500]}", flush=True)

        # Save all data
        with open('fl511_network.json', 'w') as f:
            json.dump({
                'requests': requests,
                'responses': responses,
                'video_elements_before_click': video_info,
                'video_elements_after_click': video_info2,
            }, f, indent=2)
        print(f'\nSaved to fl511_network.json', flush=True)

        await browser.close()

asyncio.run(main())
