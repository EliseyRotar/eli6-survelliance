"""Get full live URL for all 4,265 FL511 cams.

Now that we know the trick (send full fl511 response to divas), this should be fast.
"""
import asyncio
import csv
import json
import os
import re
import time
import random
from playwright.async_api import async_playwright

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
FL511_DATA = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_cams_with_live.json'
PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_divas_full_tokens.json'
LOG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\archive/logs\fl511_divas_full_log.txt'


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
        cams = json.load(f)
    cams = [c for c in cams if c.get('video_url_template')]
    log(f'Loaded {len(cams):,} cams with templates')

    # Load progress
    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS) as f:
                progress = json.load(f)
        except:
            pass
    log(f'  {len(progress):,} already have full live URLs')

    to_query = [c for c in cams if str(c['cam_id']) not in progress]
    log(f'  Need to query: {len(to_query):,}')

    if not to_query:
        log('All done!')
        await build_csv(progress, cams)
        return

    # Setup browser
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
        csrf = await page.evaluate('''() => {
            const meta = document.querySelector('input[name="__RequestVerificationToken"]');
            return meta ? meta.value : null;
        }''')
        log(f'  Token: {csrf[:30] if csrf else "NONE"}...')

        t0 = time.time()
        n_done = 0
        n_success = 0
        n_fail = 0
        last_save = time.time()
        errors = 0

        for i, c in enumerate(to_query):
            cam_id = str(c['cam_id'])
            image_id = c.get('image_id')
            template = c.get('video_url_template', '')

            if not template:
                continue

            success = False
            for retry in range(3):
                try:
                    # Step 1: Get full fl511 response
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

                    # Step 2: Send FULL response to divas
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

                    if isinstance(divas, dict) and 'error' in divas:
                        await asyncio.sleep(2 + retry * 2)
                        continue
                    # Parse token
                    m = re.search(r'token=([A-Fa-f0-9]+)', divas)
                    if m:
                        dt = m.group(1)
                        sep = '&' if '?' in template else '?'
                        full_url = f'{template}{sep}token={dt}'
                        progress[cam_id] = {
                            'live_url': full_url,
                            'template': template,
                            'divas_token': dt,
                            'fl_token': result.get('token', ''),
                            'sourceId': c.get('sourceId'),
                            'timestamp': time.time(),
                        }
                        n_success += 1
                        success = True
                        break
                    await asyncio.sleep(2 + retry * 2)
                except Exception as e:
                    log(f'  Err for cam {cam_id}: {e}')
                    await asyncio.sleep(2 + retry * 2)

            if not success:
                progress[cam_id] = {
                    'live_url': template,
                    'template': template,
                    'divas_token': '',
                    'fl_token': '',
                    'sourceId': c.get('sourceId'),
                    'timestamp': time.time(),
                    'no_token': True,
                }
                n_fail += 1
                errors += 1
                if errors >= 5:
                    log('  Too many errors, refresh session')
                    try:
                        await page.reload(wait_until='domcontentloaded', timeout=60000)
                        await asyncio.sleep(20)
                        csrf = await page.evaluate('''() => {
                            const meta = document.querySelector('input[name="__RequestVerificationToken"]');
                            return meta ? meta.value : null;
                        }''')
                        log(f'  Refreshed, new token: {csrf[:30] if csrf else "None"}...')
                        errors = 0
                    except:
                        pass

            n_done += 1
            if n_done % 50 == 0:
                elapsed = time.time() - t0
                rate = n_done / max(elapsed, 1)
                log(f'  {n_done:,}/{len(to_query):,} ({n_success:,} ok, {n_fail:,} fail) {rate:.1f}/s')
                with open(PROGRESS, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, indent=2)
                last_save = time.time()

            await asyncio.sleep(0.4)  # Rate limit

        # Final save
        with open(PROGRESS, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        elapsed = time.time() - t0
        log(f'\n[DONE] {n_done:,} cams, {n_success:,} with divas token, {n_fail:,} fail, in {elapsed:.0f}s')

        await browser.close()

    # Build CSV
    await build_csv(progress, cams)


async def build_csv(progress, cams):
    """Update master CSV with full live URLs."""
    log('\n[BUILD] Updating master CSV with full live URLs...')

    # Build map: location -> live URL
    live_by_location = {}
    for c in cams:
        loc = c.get('location', '').strip()
        if not loc:
            continue
        cid = str(c['cam_id'])
        if cid in progress:
            url = progress[cid].get('live_url', '')
            if url:
                live_by_location[loc] = url

    log(f'  {len(live_by_location):,} locations with live URLs')

    csv.field_size_limit(2**31 - 1)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames

    fl511_rows = [(i, r) for i, r in enumerate(rows) if (r.get('host', '') or '').lower() == 'fl511.com']
    log(f'  {len(fl511_rows):,} fl511 rows in CSV')

    n_updated = 0
    for i, row in fl511_rows:
        desc = (row.get('description', '') or '').strip()
        title = (row.get('page_title', '') or '').strip()
        notes = row.get('notes', '') or ''

        match = None
        for key in (desc, title):
            if key and key in live_by_location:
                match = live_by_location[key]
                break
        if not match:
            for loc, url in live_by_location.items():
                if loc and (loc in desc or loc in title):
                    match = url
                    break

        if match:
            rows[i]['live_stream_url'] = match
            rows[i]['url'] = match
            rows[i]['type'] = 'video-hls'
            existing_notes = rows[i].get('notes', '') or ''
            if 'fl511_full_live' not in existing_notes:
                rows[i]['notes'] = existing_notes + ' | fl511_full_live'
            n_updated += 1

    log(f'  Updated {n_updated} of {len(fl511_rows)} rows')

    # Save
    tmp = CSV_PATH + '.tmp'
    for attempt in range(20):
        try:
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                w.writerows(rows)
            os.replace(tmp, CSV_PATH)
            log(f'  Saved CSV with {n_updated} fl511 rows updated')
            return
        except PermissionError:
            time.sleep(2 + random.uniform(0, 3))
    log('  ERROR: Could not save CSV')


if __name__ == '__main__':
    asyncio.run(main())
