"""For each fl511 cam, fetch the live HLS URL via /Camera/GetVideoUrl?imageId=X.

Then update master CSV to replace still image URLs with live HLS URLs.
"""
import asyncio
import json
import os
import time
import re
import csv
import random
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
FL511_DATA = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_cams_all.json'
PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_live_progress.json'
LOG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\archive/logs\fl511_live_log.txt'


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass


async def main():
    # Load fl511 cams
    with open(FL511_DATA, encoding='utf-8') as f:
        data = json.load(f)
    cams = data.get('cams', [])
    log(f'Loaded {len(cams):,} fl511 cams')

    # Filter to those with imageId and not already a videoUrl
    to_query = []
    for c in cams:
        images = c.get('images') or []
        if not images:
            continue
        img = images[0]
        image_id = img.get('id')
        if not image_id:
            continue
        # Skip if videoUrl already in record
        if img.get('videoUrl'):
            continue
        # Skip if isVideoAuthRequired is false (no video)
        if not img.get('isVideoAuthRequired', True):
            continue
        to_query.append((image_id, c.get('id'), c.get('location', ''), c.get('source', '')))

    log(f'  {len(to_query):,} need live URL query')

    # Load progress
    progress = {'queried': {}}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS, encoding='utf-8') as f:
                progress = json.load(f)
        except:
            pass
    log(f'  {len(progress.get("queried", {})):,} already queried')

    # Setup Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Get session
        log('Getting fl511 session...')
        try:
            await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            log(f'  goto err: {e}')
        await asyncio.sleep(30)

        token = await page.evaluate('''() => {
            const meta = document.querySelector('input[name="__RequestVerificationToken"]');
            return meta ? meta.value : null;
        }''')
        log(f'  Token: {token[:30] if token else "NONE"}...')

        # Query each cam
        t0 = time.time()
        n_done = 0
        n_success = 0
        n_fail = 0
        errors = 0
        last_save = time.time()

        for image_id, cam_id, location, source in to_query:
            if str(image_id) in progress['queried']:
                continue

            success = False
            for retry in range(3):
                try:
                    result = await page.evaluate('''async (args) => {
                        const { imageId, token } = args;
                        try {
                            const r = await fetch(`https://fl511.com/Camera/GetVideoUrl?imageId=${imageId}&_=${Date.now()}`, {
                                headers: {
                                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                                    'X-Requested-With': 'XMLHttpRequest',
                                    '__RequestVerificationToken': token,
                                }
                            });
                            if (!r.ok) return { error: r.status };
                            return await r.json();
                        } catch (e) {
                            return { error: e.message };
                        }
                    }''', {'imageId': image_id, 'token': token})

                    if isinstance(result, dict) and result.get('error'):
                        log(f'  Retry {retry+1}/3 for {image_id}: {result["error"]}')
                        await asyncio.sleep(2 ** retry)
                    elif isinstance(result, dict):
                        progress['queried'][str(image_id)] = {
                            'cam_id': cam_id,
                            'location': location,
                            'source': source,
                            'video_url': result.get('videoUrl') or result.get('videoURL') or result.get('url') or '',
                            'result': result,
                            'timestamp': time.time(),
                        }
                        if progress['queried'][str(image_id)]['video_url']:
                            n_success += 1
                        else:
                            n_fail += 1
                        success = True
                        break
                    else:
                        log(f'  Retry {retry+1}/3 for {image_id}: bad response {type(result)}')
                        await asyncio.sleep(2 ** retry)
                except Exception as e:
                    log(f'  Retry {retry+1}/3 for {image_id}: {e}')
                    await asyncio.sleep(2 ** retry)

            if not success:
                progress['queried'][str(image_id)] = {
                    'cam_id': cam_id,
                    'location': location,
                    'source': source,
                    'video_url': '',
                    'result': {'error': 'max_retries'},
                    'timestamp': time.time(),
                }
                n_fail += 1
                errors += 1
                if errors >= 5:
                    log('  Too many errors, refresh session')
                    try:
                        await page.reload(wait_until='domcontentloaded', timeout=60000)
                        await asyncio.sleep(20)
                        token = await page.evaluate('''() => {
                            const meta = document.querySelector('input[name="__RequestVerificationToken"]');
                            return meta ? meta.value : null;
                        }''')
                        log(f'  Refreshed, new token: {token[:30] if token else "None"}...')
                        errors = 0
                    except:
                        pass

            n_done += 1
            if n_done % 50 == 0:
                elapsed = time.time() - t0
                rate = n_done / max(elapsed, 1)
                log(f'  {n_done:,}/{len(to_query):,} done ({n_success:,} ok, {n_fail:,} fail) {rate:.0f}/s')

            if time.time() - last_save > 60:
                with open(PROGRESS, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, indent=2)
                last_save = time.time()

            await asyncio.sleep(0.3)  # Rate limit

        # Final save
        with open(PROGRESS, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        elapsed = time.time() - t0
        log(f'\n[DONE] {n_done:,} cams, {n_success:,} with live URL, {n_fail:,} fail, in {elapsed:.0f}s')

        # Stats on result format
        sample_result = None
        for v in progress['queried'].values():
            if v.get('video_url'):
                sample_result = v
                break
        if sample_result:
            log(f'Sample result:')
            log(f'  video_url: {sample_result["video_url"]}')
            log(f'  full: {sample_result["result"]}')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
