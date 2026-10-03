"""For each fl511 cam with videoUrl template, fetch the divas token and build full m3u8 URL.

Then update master CSV.

Process:
1. For each cam with template, POST token to divas.cloud/VDS-API/SecureTokenUri/GetSecureTokenUriBySourceId
   - Use the sourceId from the cam
2. Build full m3u8 URL: {template}?token={secure_token}
3. Update CSV
"""
import asyncio
import csv
import json
import os
import re
import time
import random
from playwright.async_api import async_playwright
from collections import Counter

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
FL511_LIVE = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_cams_with_live.json'
PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_divas_tokens.json'
LOG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\archive/logs\fl511_divas_log.txt'


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass


async def main():
    # Load enriched fl511 data
    with open(FL511_LIVE, encoding='utf-8') as f:
        cams = json.load(f)
    log(f'Loaded {len(cams):,} fl511 cams')

    # Load progress
    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS, encoding='utf-8') as f:
                progress = json.load(f)
        except:
            pass
    log(f'  Already have {len(progress):,} divas tokens')

    # Filter to those we need to query
    to_query = [c for c in cams if c.get('fl_token') and str(c['cam_id']) not in progress]
    log(f'  Need to query {len(to_query):,} for divas tokens')

    if not to_query:
        log('All done, building CSV')
        await build_csv(progress, cams)
        return

    # Setup browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

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

        t0 = time.time()
        n_done = 0
        n_success = 0
        n_fail = 0
        errors = 0
        last_save = time.time()

        for c in to_query:
            cam_id = str(c['cam_id'])
            fl_token = c.get('fl_token', '')

            success = False
            for retry in range(3):
                try:
                    # Step 1: Call fl511 GetVideoUrl to get the chan (or use what we have)
                    # We have the fl_token. Need to call divas to get secure token
                    # POST to divas.cloud
                    result = await page.evaluate('''async (args) => {
                        const { token, flToken } = args;
                        try {
                            const r = await fetch('https://divas.cloud/VDS-API/SecureTokenUri/GetSecureTokenUriBySourceId', {
                                method: 'POST',
                                headers: {
                                    'Accept': '*/*',
                                    'Origin': 'https://fl511.com',
                                    'Referer': 'https://fl511.com/',
                                    'Content-Type': 'application/json',
                                    '__RequestVerificationToken': token,
                                },
                                body: JSON.stringify({ token: flToken }),
                                credentials: 'omit',
                            });
                            if (!r.ok) return { error: r.status };
                            return await r.json();
                        } catch (e) {
                            return { error: e.message };
                        }
                    }''', {'token': token, 'flToken': fl_token})

                    if isinstance(result, dict) and 'error' not in result:
                        # The response is "?token=..." or {"token": "..."}
                        token_str = ''
                        if 'token' in result:
                            token_str = result['token']
                        elif isinstance(result, str):
                            token_str = result.replace('?token=', '').strip()
                        progress[cam_id] = {
                            'divas_token': token_str,
                            'fl_token': fl_token,
                            'sourceId': c.get('sourceId'),
                            'timestamp': time.time(),
                        }
                        n_success += 1
                        success = True
                        break
                    else:
                        log(f'  Retry {retry+1}/3 for cam {cam_id}: {result}')
                        await asyncio.sleep(2 + 2 ** retry)
                except Exception as e:
                    log(f'  Retry {retry+1}/3 for cam {cam_id}: {e}')
                    await asyncio.sleep(2 ** retry)

            if not success:
                progress[cam_id] = {'error': 'max_retries', 'timestamp': time.time()}
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
            if n_done % 20 == 0:
                elapsed = time.time() - t0
                rate = n_done / max(elapsed, 1)
                log(f'  {n_done:,}/{len(to_query):,} done ({n_success:,} ok, {n_fail:,} fail) {rate:.0f}/s')

            if time.time() - last_save > 60:
                with open(PROGRESS, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, indent=2)
                last_save = time.time()

            await asyncio.sleep(0.3)

        # Final save
        with open(PROGRESS, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        elapsed = time.time() - t0
        log(f'\n[DONE] {n_done:,} cams, {n_success:,} with divas token, {n_fail:,} fail, in {elapsed:.0f}s')

        await browser.close()

    # Build CSV updates
    await build_csv(progress, cams)


async def build_csv(progress, cams):
    """Build the CSV update list."""
    log('\n[BUILD] Building CSV update data...')
    # For each cam, determine the full live URL
    updates = []
    for c in cams:
        cam_id = str(c['cam_id'])
        template = c.get('video_url_template', '')
        divas_token_data = progress.get(cam_id, {})
        divas_token = divas_token_data.get('divas_token', '') if isinstance(divas_token_data, dict) else ''

        if template and divas_token:
            # Full URL with token
            sep = '&' if '?' in template else '?'
            full_url = f'{template}{sep}token={divas_token}'
        elif template:
            # Template but no token (still has chan-N)
            full_url = template
        else:
            full_url = ''

        if full_url:
            updates.append({
                'fl511_cam_id': cam_id,
                'image_id': c.get('image_id'),
                'live_url': full_url,
                'location': c.get('location', ''),
                'county': c.get('county', ''),
                'region': c.get('region', ''),
                'description': c.get('description', ''),
                'source': c.get('source', ''),
            })

    log(f'  {len(updates):,} cams with live URLs')

    # Save
    with open('fl511_live_urls.json', 'w', encoding='utf-8') as f:
        json.dump(updates, f, indent=2, ensure_ascii=False)
    log(f'  Saved to fl511_live_urls.json')

    # Update CSV
    log('\n[CSV] Updating master CSV...')
    csv.field_size_limit(2**31 - 1)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames

    # Build map: fl511_cam_id -> URL
    # First, find the existing fl511 entries - they have notes with argus_id=opencctv_state511_s511-FL-N
    # We need to match by FL cam ID somehow. The notes might say "FL-1219" but we need imageId
    # Better approach: look at hostname fl511.com:443 entries and add live URLs by matching source/systemSourceId

    # Save the update map for separate processing
    fl511_by_id = {u['fl511_cam_id']: u for u in updates}

    # Read the current CSV and find all fl511 rows
    # They have notes with argus_id like "opencctv_state511_s511-FL-1219" or similar
    # We need to match by sourceId since the description in fl511 data matches

    n_updated = 0
    for row in rows:
        if row.get('host', '').lower() == 'fl511.com':
            # This is a fl511 row. We need to know which cam this is.
            # Look at the live_stream_url or notes for clues
            # The notes have argus_id=opencctv_state511_s511-FL-NNNN
            notes = row.get('notes', '') or ''
            url = row.get('url', '') or ''
            # The fl511.com:443 URL is generic
            # We can match by checking if the cam's description matches the row's title or location
            # For now, skip - we'll match separately using the cam_id mapping

    log(f'  Found {sum(1 for r in rows if (r.get("host","") or "").lower() == "fl511.com")} fl511 rows in CSV')

    log('\n[OK] Live URLs saved to fl511_live_urls.json. Need to match to existing CSV rows.')


if __name__ == '__main__':
    asyncio.run(main())
