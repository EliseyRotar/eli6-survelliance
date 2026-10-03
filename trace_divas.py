"""Careful trace of divas request."""
import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture with body
        bodies = []
        async def on_request_finished(req):
            try:
                if 'divas.cloud/VDS-API' in req.url:
                    body = req.post_data
                    bodies.append({
                        'url': req.url,
                        'body': body,
                        'headers': await req.all_headers(),
                    })
            except:
                pass
        page.on('requestfinished', on_request_finished)

        try:
            await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(30)

        token = await page.evaluate('''() => {
            const meta = document.querySelector('input[name="__RequestVerificationToken"]');
            return meta ? meta.value : null;
        }''')
        print(f'Token: {token[:30] if token else "NONE"}...', flush=True)

        # Get fl_token for imageId=615
        result = await page.evaluate('''async (args) => {
            const { imageId, token } = args;
            const r = await fetch(`https://fl511.com/Camera/GetVideoUrl?imageId=${imageId}&_=${Date.now()}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    '__RequestVerificationToken': token,
                }
            });
            return await r.json();
        }''', {'imageId': 615, 'token': token})
        fl_token = result.get('token', '')
        print(f'fl_token: {fl_token}', flush=True)

        # Now POST to divas
        bodies.clear()
        print(f'\nPosting to divas...', flush=True)
        divas = await page.evaluate('''async (args) => {
            const { flToken, token } = args;
            const r = await fetch('https://divas.cloud/VDS-API/SecureTokenUri/GetSecureTokenUriBySourceId', {
                method: 'POST',
                headers: {
                    'Origin': 'https://fl511.com',
                    'Referer': 'https://fl511.com/',
                    'Content-Type': 'application/json',
                    '__RequestVerificationToken': token,
                },
                body: JSON.stringify({ token: flToken }),
            });
            return { status: r.status, body: await r.text() };
        }''', {'flToken': fl_token, 'token': token})
        await asyncio.sleep(3)
        print(f'  divas: {divas}', flush=True)

        print(f'\nCaptured {len(bodies)} divas requests', flush=True)
        for b in bodies:
            print(f'\nURL: {b["url"]}', flush=True)
            print(f'Body: {b["body"]}', flush=True)
            print(f'Headers:', flush=True)
            for k, v in b['headers'].items():
                print(f'  {k}: {v[:200]}', flush=True)

        await browser.close()

asyncio.run(main())
