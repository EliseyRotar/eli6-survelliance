"""Find TV's actual data endpoint by capturing browser network traffic."""
import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        # Set the Firebase ID token
        with open('camera_testing/tv_auth.json') as f:
            auth = json.load(f)
        id_token = auth.get('idToken', '')

        # Capture network
        requests = []
        async def on_request(req):
            if 'trafficvision' in req.url:
                requests.append({
                    'url': req.url,
                    'method': req.method,
                    'headers': await req.all_headers(),
                })
        page.on('request', on_request)

        # First set the auth in localStorage/sessionStorage
        print('[1] Going to trafficvision.live...', flush=True)
        try:
            await page.goto('https://trafficvision.live/', wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(15)

        # Try to load the camera data via fetch
        print('\n[2] Injecting fetch calls...', flush=True)
        result = await page.evaluate('''async (token) => {
            // Try direct fetch with bearer
            const urls = [
                'https://trafficvision.live/api/v1/cameras',
                'https://api.trafficvision.live/v1/cameras',
                'https://api.trafficvision.live/cameras',
                'https://trafficvision.live/api/cameras',
                'https://trafficvision.live/api/catalog',
            ];
            const out = [];
            for (const url of urls) {
                try {
                    const r = await fetch(url, {
                        headers: {
                            'Accept': 'application/json',
                            'Authorization': 'Bearer ' + token,
                        }
                    });
                    out.push({ url, status: r.status, ct: r.headers.get('content-type'), body: (await r.text()).slice(0, 300) });
                } catch (e) {
                    out.push({ url, err: e.message });
                }
            }
            return out;
        }''', id_token)

        for r in result:
            print(f'  {r.get("url", "?")}', flush=True)
            if 'status' in r:
                print(f'    {r["status"]} {r.get("ct", "")} {r.get("body", "")[:200]}', flush=True)
            else:
                print(f'    ERR: {r.get("err")}', flush=True)

        # Also: any requests captured that look like API?
        print(f'\n[3] Captured requests to trafficvision (first 50):', flush=True)
        for r in requests[:50]:
            if '/api/' in r['url'] or '/v1/' in r['url']:
                print(f'  [{r["method"]}] {r["url"][:200]}', flush=True)
                # Show auth header
                auth = r['headers'].get('authorization', '')
                if auth:
                    print(f'    Auth: {auth[:80]}', flush=True)

        # Save
        with open('tv_api_capture.json', 'w') as f:
            json.dump(requests, f, indent=2)
        print(f'\n  Saved {len(requests)} requests', flush=True)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
