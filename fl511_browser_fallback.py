"""Browser-based fallback for cams that fail with direct API.

The browser session has different rate limits and may succeed.
"""
import asyncio
import json
import os
import re
import time
from playwright.async_api import async_playwright

PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_divas_full_tokens.json'
PROGRESS_BROWSER = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_divas_browser.json'


async def main():
    # Load progress from both files
    progress = {}
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            progress = json.load(f)
    if os.path.exists(PROGRESS_BROWSER):
        with open(PROGRESS_BROWSER) as f:
            browser_progress = json.load(f)
        # Merge - don't overwrite if progress already has divas_token
        for k, v in browser_progress.items():
            if k not in progress or not progress[k].get('divas_token'):
                progress[k] = v
    # Find cams without tokens
    no_token = []
    with open('fl511_cams_with_live.json', encoding='utf-8') as f:
        cams = json.load(f)
    for c in cams:
        if not c.get('video_url_template'):
            continue
        cid = str(c['cam_id'])
        if cid in progress and progress[cid].get('divas_token'):
            continue
        no_token.append(c)
    print(f'Cams needing token: {len(no_token):,}', flush=True)

    if not no_token:
        print('All done!', flush=True)
        return

    # Need a session lock for atomic file writes
    import threading
    write_lock = threading.Lock()
    last_save_time = [time.time()]

    def save_progress_atomic():
        """Save progress atomically to BROWSER file (not main)."""
        with write_lock:
            tmp = PROGRESS_BROWSER + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(progress, f, indent=2)
            try:
                os.replace(tmp, PROGRESS_BROWSER)
            except OSError:
                pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Get session
        print('Getting session...', flush=True)
        try:
            await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(30)
        try:
            await page.reload(wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(20)

        csrf = await page.evaluate('''() => {
            const meta = document.querySelector('input[name="__RequestVerificationToken"]');
            return meta ? meta.value : null;
        }''')
        print(f'Token: {csrf[:30] if csrf else "NONE"}...', flush=True)

        t0 = time.time()
        n_done = 0
        n_success = 0
        n_fail = 0
        last_save = time.time()

        for c in no_token:
            cam_id = str(c['cam_id'])
            image_id = c.get('image_id')
            template = c.get('video_url_template', '')

            if not image_id or not template:
                continue

            # Already have a working divas_token from direct? Skip
            cur = progress.get(cam_id, {})
            if cur.get('divas_token') and not cur.get('no_token'):
                continue

            success = False
            for retry in range(2):
                try:
                    result = await page.evaluate('''async (args) => {
                        const { imageId, token } = args;
                        try {
                            const r = await fetch(`https://fl511.com/Camera/GetVideoUrl?imageId=${imageId}&_=${Date.now()}`, {
                                headers: {
                                    'X-Requested-With': 'XMLHttpRequest',
                                    '__RequestVerificationToken': token,
                                }
                            });
                            if (!r.ok) return { error: r.status };
                            return await r.json();
                        } catch (e) {
                            return { error: e.message };
                        }
                    }''', {'imageId': image_id, 'token': csrf})

                    if not isinstance(result, dict) or 'error' in result or 'token' not in result:
                        await asyncio.sleep(2 + retry * 2)
                        continue

                    divas = await page.evaluate('''async (args) => {
                        const { body, token } = args;
                        const r = await fetch('https://divas.cloud/VDS-API/SecureTokenUri/GetSecureTokenUriBySourceId', {
                            method: 'POST',
                            headers: {
                                'Origin': 'https://fl511.com',
                                'Referer': 'https://fl511.com/',
                                'Content-Type': 'application/json',
                                '__RequestVerificationToken': token,
                            },
                            body: JSON.stringify(body),
                        });
                        if (!r.ok) return { error: r.status };
                        return await r.text();
                    }''', {'body': result, 'token': csrf})

                    if isinstance(divas, dict):
                        await asyncio.sleep(2 + retry * 2)
                        continue
                    m = re.search(r'token=([A-Fa-f0-9]+)', divas)
                    if m:
                        dt = m.group(1)
                        sep = '&' if '?' in template else '?'
                        full_url = f'{template}{sep}token={dt}'
                        progress[cam_id] = {
                            'live_url': full_url,
                            'divas_token': dt,
                            'fl_token': result.get('token', ''),
                            'sourceId': c.get('sourceId'),
                            'timestamp': time.time(),
                            'via_browser': True,
                        }
                        n_success += 1
                        success = True
                        break
                    await asyncio.sleep(2 + retry * 2)
                except Exception as e:
                    print(f'  Err for {cam_id}: {e}', flush=True)
                    await asyncio.sleep(2 + retry * 2)

            if not success:
                # Only set no_token if we don't already have a real URL
                if not progress.get(cam_id, {}).get('divas_token'):
                    progress[cam_id] = {
                        'live_url': template,
                        'no_token': True,
                        'timestamp': time.time(),
                    }
                n_fail += 1

            n_done += 1
            if n_done % 20 == 0:
                elapsed = time.time() - t0
                rate = n_done / max(elapsed, 1)
                print(f'  {n_done}/{len(no_token)} ({n_success} ok, {n_fail} fail) {rate:.1f}/s', flush=True)
                save_progress_atomic()
                last_save = time.time()

            await asyncio.sleep(0.5)

        # Final save
        save_progress_atomic()
        elapsed = time.time() - t0
        print(f'\n[DONE] {n_done} cams, {n_success} with token, in {elapsed:.0f}s', flush=True)

        await browser.close()


asyncio.run(main())
