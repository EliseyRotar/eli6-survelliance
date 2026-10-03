"""Navigate to a TV page that triggers catalog fetch, capture network."""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        # Capture all
        manifests = []
        shards = []
        session = []

        async def on_response(resp):
            url = resp.url
            if '/internal/manifest' in url and 'manifest' in url:
                try:
                    body = await resp.text()
                    manifests.append({'url': url, 'status': resp.status, 'body': body[:300]})
                except:
                    pass
            elif '/internal/catalog/shards/' in url:
                try:
                    body = await resp.text()
                    shards.append({'url': url, 'status': resp.status, 'size': len(body)})
                except:
                    pass
            elif '/api/session' in url:
                try:
                    body = await resp.text()
                    session.append({'url': url, 'status': resp.status, 'body': body[:300]})
                except:
                    pass

        page.on('response', on_response)

        # Navigate
        print('[1] Going to /cameras to trigger catalog fetch...', flush=True)
        try:
            await page.goto('https://trafficvision.live/cameras', wait_until='domcontentloaded', timeout=90000)
        except Exception as e:
            print(f'  goto err: {e}', flush=True)
        await asyncio.sleep(45)
        print(f'  URL: {page.url}', flush=True)

        # Print captured
        print(f'\n[2] Captured: {len(manifests)} manifests, {len(shards)} shards, {len(session)} session', flush=True)
        for m in manifests:
            print(f'  Manifest: {m["url"][:200]} -> {m["status"]}', flush=True)
            print(f'    Body: {m["body"][:300]}', flush=True)
        for s in session:
            print(f'  Session: {s["url"]} -> {s["status"]}', flush=True)
            print(f'    Body: {s["body"][:300]}', flush=True)
        print(f'  Shards (first 15):', flush=True)
        for s in shards[:15]:
            print(f'    {s["url"][:200]} -> {s["status"]} ({s["size"]/1024/1024:.1f}MB)', flush=True)
        print(f'  ... {len(shards) - 15} more', flush=True)

        # Save
        with open('tv_capture_v2.json', 'w') as f:
            json.dump({'manifests': manifests, 'shards': shards, 'session': session}, f, indent=2)
        print(f'  Saved to tv_capture_v2.json', flush=True)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
