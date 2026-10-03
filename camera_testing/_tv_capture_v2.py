"""Capture fresh TrafficVision.Live catalog using Playwright + saved auth.

Strategy:
1. Load cookies (cf_clearance) for Cloudflare bypass
2. Use the saved Firebase idToken to authenticate via JS injection
3. Wait for the SPA to fetch all shards
4. Save everything
"""
import asyncio
import json
import os
import re
import time

SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards_2026_09_12'
OUTPUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_2026_09_12.json'
AUTH_FILE = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json'
COOKIES_FILE = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_cookies.json'

os.makedirs(SHARDS_DIR, exist_ok=True)

with open(AUTH_FILE) as f:
    auth = json.load(f)
ID_TOKEN = auth['idToken']
REFRESH_TOKEN = auth.get('refreshToken', '')
EMAIL = auth.get('email', '')
PASSWORD = 'Tp?kKD)Y>ya5:s%'
API_KEY = 'AIzaSyAcfux4lyS-IlYdYMhkxa1u5WRxI9-0RnY'

print(f'Auth: email={EMAIL}, idToken={ID_TOKEN[:50]}...')
print(f'Saving to: {SHARDS_DIR}')


async def capture_full():
    from playwright.async_api import async_playwright

    captured = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled'],
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        )

        # Load existing cookies
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE) as f:
                cookies = json.load(f)
            try:
                await context.add_cookies(cookies)
                print(f'  loaded {len(cookies)} cookies')
            except Exception as e:
                print(f'  cookie err: {e}')

        page = await context.new_page()

        # Capture responses
        async def capture(response):
            try:
                url = response.url
                # Match: catalog/shards, internal/manifest, internal/catalog
                if (response.status == 200 and
                    ('/catalog/shards/' in url or
                     '/internal/manifest' in url or
                     '/internal/catalog' in url or
                     url.endswith('manifest.json'))):
                    try:
                        body = await response.body()
                        captured[url] = body
                        print(f'  captured: {url.split("/")[-1]} ({len(body):,} bytes)', flush=True)
                    except Exception as e:
                        print(f'  body err: {e}', flush=True)
            except Exception:
                pass
        page.on('response', capture)

        # Step 1: Load homepage
        print('\n[1/4] Loading homepage...')
        await page.goto('https://trafficvision.live/', timeout=60000, wait_until='domcontentloaded')
        await asyncio.sleep(5)

        # Step 2: Sign in via Firebase REST
        print('\n[2/4] Signing in via Firebase REST...')
        signin_resp = await page.evaluate(f'''
        async () => {{
            try {{
                const r = await fetch('https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        email: '{EMAIL}',
                        password: '{PASSWORD}',
                        returnSecureToken: true
                    }})
                }});
                const data = await r.json();
                if (data.error) return {{ ok: false, err: data.error.message }};
                // Save token in window for next call
                window.__tv_idToken = data.idToken;
                window.__tv_refreshToken = data.refreshToken;
                return {{ ok: true, uid: data.localId, expires: data.expiresIn }};
            }} catch (e) {{
                return {{ ok: false, err: String(e) }};
            }}
        }}
        ''')
        print(f'  signin: {signin_resp}')
        if not signin_resp.get('ok'):
            print('SIGNIN FAILED - aborting')
            await browser.close()
            return

        # Save fresh auth
        with open(AUTH_FILE, 'w') as f:
            json.dump({
                'kind': 'identitytoolkit#VerifyPasswordResponse',
                'localId': signin_resp.get('uid', ''),
                'email': EMAIL,
                'idToken': signin_resp.get('idToken', ''),
                'refreshToken': signin_resp.get('refreshToken', ''),
                'expiresIn': str(signin_resp.get('expires', 3600)),
            }, f, indent=2)
        print('  fresh auth saved')

        # Step 3: Inject auth into Firebase SDK in browser
        print('\n[3/4] Setting Firebase auth in browser...')
        # Firebase Auth persists in IndexedDB. We need to sign in via the SDK so
        # subsequent Firestore calls have the auth token.
        # Approach: navigate to home, then sign in via the auth context.
        # The SPA's own login button is hidden. We can use the JS SDK directly.
        set_auth_script = f'''
        async () => {{
            try {{
                // Try to find the firebase auth instance
                const mod = await import('/assets/firebase-CvJ35x5S.js');
                const {{ initializeApp, getApps }} = mod;
                const {{ getAuth, signInWithCustomToken }} = await import('https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js');
                // Get the existing app from the page
                let app;
                const apps = getApps();
                if (apps.length > 0) {{
                    app = apps[0];
                }} else {{
                    return {{ ok: false, err: 'no firebase app' }};
                }}
                const auth = getAuth(app);
                // Sign in with the custom token (we have idToken but need a custom token)
                // Actually Firebase supports signInWithIdToken... no
                // Use the signInWithCustomToken method requires a custom token from server
                // But we can use the REST API to set the auth state directly via IndexedDB
                // Simpler: signInWithEmailAndPassword
                const {{ signInWithEmailAndPassword }} = await import('https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js');
                const cred = await signInWithEmailAndPassword(auth, '{EMAIL}', '{PASSWORD}');
                return {{ ok: true, uid: cred.user.uid }};
            }} catch (e) {{
                return {{ ok: false, err: String(e).slice(0, 300) }};
            }}
        }}
        '''
        result = await page.evaluate(set_auth_script)
        print(f'  set auth: {result}')

        # Step 4: Reload to trigger fresh catalog load
        print('\n[4/4] Reloading to load fresh catalog...')
        await page.reload(wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(5)

        # Wait for shards to load
        for i in range(90):  # 90s
            await asyncio.sleep(1)
            n = len(captured)
            if i % 5 == 0 or n >= 12:
                print(f'  [{i+1}s] {n} captured')
            if n >= 12:
                print('  All expected shards captured!')
                break
        # Final wait
        await asyncio.sleep(15)
        print(f'\nTotal captured: {len(captured)}')
        total_bytes = sum(len(b) for b in captured.values())
        print(f'Total bytes: {total_bytes:,}')

        # Save cookies
        cookies = await context.cookies()
        with open(COOKIES_FILE, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f'Saved {len(cookies)} cookies')

        await browser.close()

    # Save shard files and combine
    full_cams = []
    for url, body in captured.items():
        name = url.split('/')[-1] or 'unknown.bin'
        name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
        path = os.path.join(SHARDS_DIR, name)
        with open(path, 'wb') as f:
            f.write(body)
        if '/catalog/shards/' in url or (b'"cameras"' in body[:1000]):
            try:
                d = json.loads(body.decode('utf-8', errors='replace'))
                cams = d.get('cameras', [])
                full_cams.extend(cams)
                print(f'  {name}: {len(cams)} cams')
            except Exception as e:
                print(f'  parse err {name}: {e}')

    print(f'\nTotal cameras: {len(full_cams)}')
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({'cameras': full_cams}, f, ensure_ascii=False)
    print(f'Saved to {OUTPUT}')


if __name__ == '__main__':
    asyncio.run(capture_full())
