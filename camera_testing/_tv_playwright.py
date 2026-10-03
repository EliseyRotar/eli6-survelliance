"""Use Playwright to log into trafficvision.live and scrape the SPA catalog."""
import asyncio
import json
import os
import sys
import time

EMAIL = 'fohot18565@kolsea.com'
PASSWORD = 'Tp?kKD)Y>ya5:s%'
AUTH_FILE = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json'
COOKIES_FILE = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_cookies.json'
AUTH_STATE_FILE = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_storage.json'


async def login_and_extract():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        )
        page = await context.new_page()

        # Watch all network requests
        captured_responses = []
        async def capture_response(response):
            try:
                ct = response.headers.get('content-type', '')
                url = response.url
                if 'trafficvision.live' in url or 'firestore' in url:
                    if 'json' in ct.lower() or 'firestore' in url or 'rtdb' in url or 'app.trafficvision' in url:
                        try:
                            body = await response.text()
                            captured_responses.append({'url': url, 'status': response.status, 'body': body[:50000]})
                            print(f'Captured: {url[:120]} ({len(body)} bytes)')
                        except Exception as e:
                            pass
            except Exception:
                pass
        page.on('response', capture_response)

        # Step 1: Go to homepage (triggers Cloudflare clearance)
        print('Navigating to homepage...')
        await page.goto('https://trafficvision.live/', timeout=60000, wait_until='networkidle')
        await asyncio.sleep(3)

        # Step 2: Go to auth modal — try the signin route
        print('Looking for sign-in flow...')
        # TV uses an auth modal, not a separate page
        await page.goto('https://trafficvision.live/', timeout=60000, wait_until='networkidle')

        # Inject login by calling Firebase SDK directly in page context
        await page.wait_for_timeout(3000)

        # Try to find the auth modal trigger
        try:
            # Look for any "sign in" or "log in" button
            for selector in ['button:has-text("Sign in")', 'button:has-text("Log in")', '[data-testid="signin"]', 'a:has-text("Sign in")']:
                el = await page.query_selector(selector)
                if el:
                    print(f'Found signin button: {selector}')
                    await el.click()
                    await asyncio.sleep(2)
                    break
        except Exception as e:
            print(f'no signin button: {e}')

        # Step 3: Use Firebase Auth in page context (we have the idToken already)
        print('Using Firebase idToken from REST auth...')
        with open(AUTH_FILE) as f:
            auth = json.load(f)
        id_token = auth['idToken']
        local_id = auth['localId']
        refresh_token = auth['refreshToken']
        api_key = 'AIzaSyAcfux4lyS-IlYdYMhkxa1u5WRxI9-0RnY'

        # Sign in via Firebase JS SDK in browser context
        signin_script = f"""
        async () => {{
            try {{
                const auth = window.firebase?.auth?.();
                if (!auth) {{
                    const mod = await import('/assets/firebase-CvumGE-S.js');
                    auth = mod.auth;
                }}
                // Sign in with custom token approach
                const cred = await auth.signInWithEmailAndPassword('{EMAIL}', '{PASSWORD}');
                window.__tv_user = cred.user;
                return {{ ok: true, uid: cred.user.uid }};
            }} catch (e) {{
                return {{ ok: false, err: String(e) }};
            }}
        }}
        """
        result = await page.evaluate(signin_script)
        print(f'Sign-in result: {result}')

        # Wait for Firestore to load cameras
        print('Waiting for Firestore to load catalog (this may take a while)...')
        await asyncio.sleep(10)

        # Try to call Firestore directly in browser context
        firestore_script = """
        async () => {
            try {
                // Look for global firestore instance
                const f = window.firebase?.firestore?.();
                if (!f) {
                    const mod = await import('/assets/firebase-CvumGE-S.js');
                    f = mod.db;
                }
                if (!f) return { ok: false, err: 'no firestore' };
                // Try common collection names
                const results = {};
                for (const col of ['cameras', 'cams', 'feeds', 'catalog', 'catalogues', 'sources', 'previewStatus']) {
                    try {
                        const snap = await f.collection(col).limit(5).get();
                        results[col] = {
                            empty: snap.empty,
                            size: snap.size,
                            sample: snap.docs.slice(0, 2).map(d => ({ id: d.id, data_keys: Object.keys(d.data() || {}) })),
                        };
                    } catch (e) {
                        results[col] = { err: String(e).slice(0, 200) };
                    }
                }
                return { ok: true, results };
            } catch (e) {
                return { ok: false, err: String(e) };
            }
        }
        """
        result = await page.evaluate(firestore_script)
        print(f'Firestore results: {json.dumps(result, indent=2)[:2000]}')

        # Save captured responses
        with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_captured.json', 'w') as f:
            json.dump(captured_responses, f, indent=2)
        print(f'Saved {len(captured_responses)} captured responses')

        # Save cookies
        cookies = await context.cookies()
        with open(COOKIES_FILE, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f'Saved {len(cookies)} cookies')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(login_and_extract())
