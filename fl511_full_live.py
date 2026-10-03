"""Update CSV with fl511 live URLs.

Strategy: For each fl511 cam with a direct videoUrl template, add it to the CSV
even if the token isn't fetched yet. Browsers can still play the HLS streams
(divas CDN may allow no-auth access for a short window after GetVideoUrl).

Also: try to fetch the token fresh from divas for the 4,265 cams.

For each cam:
1. Get fl511 token via /Camera/GetVideoUrl?imageId=X
2. POST to divas with fl_token
3. Build full m3u8 URL with token
4. Add to CSV
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
FL511_DATA = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_cams_with_live.json'
PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_full_live_progress.json'
LOG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_full_live_log.txt'


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass


async def get_divas_token(page, fl_token, csrf):
    """POST to divas to get the secure token."""
    return await page.evaluate('''async (args) => {
        const { flToken, token } = args;
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
            const txt = await r.text();
            try {
                return JSON.parse(txt);
            } catch {
                return { raw: txt };
            }
        } catch (e) {
            return { error: e.message };
        }
    }''', {'flToken': fl_token, 'token': csrf})


async def main():
    # Load fl511 cams
    with open(FL511_DATA, encoding='utf-8') as f:
        cams = json.load(f)
    log(f'Loaded {len(cams):,} fl511 cams')
    cams_with_template = [c for c in cams if c.get('video_url_template')]
    log(f'  {len(cams_with_template):,} have video_url_template')

    # Load progress
    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS, encoding='utf-8') as f:
                progress = json.load(f)
        except:
            pass
    log(f'  {len(progress):,} already have full live URLs')

    to_query = [c for c in cams_with_template if str(c['cam_id']) not in progress]
    log(f'  Need to query: {len(to_query):,}')

    if not to_query:
        log('All done, building CSV')
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

        for c in to_query:
            cam_id = str(c['cam_id'])
            template = c.get('video_url_template', '')

            if not template:
                continue

            success = False
            for retry in range(2):
                try:
                    # Get fl_token
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
                    }''', {'imageId': c['image_id'], 'token': csrf})
                    if not isinstance(result, dict) or 'error' in result or 'token' not in result:
                        await asyncio.sleep(1 + retry)
                        continue
                    fl_token = result.get('token', '')

                    # Get divas token
                    divas_result = await get_divas_token(page, fl_token, csrf)
                    if isinstance(divas_result, dict):
                        dt = ''
                        if 'token' in divas_result:
                            dt = divas_result['token']
                        elif 'raw' in divas_result:
                            # Raw string like "?token=..."
                            raw = divas_result['raw']
                            m = re.search(r'token=([A-Fa-f0-9]+)', raw)
                            if m:
                                dt = m.group(1)
                        if dt:
                            sep = '&' if '?' in template else '?'
                            full_url = f'{template}{sep}token={dt}'
                            progress[cam_id] = {
                                'live_url': full_url,
                                'template': template,
                                'fl_token': fl_token,
                                'divas_token': dt,
                                'sourceId': c.get('sourceId'),
                                'timestamp': time.time(),
                            }
                            n_success += 1
                            success = True
                            break
                    await asyncio.sleep(0.5 + retry)
                except Exception as e:
                    log(f'  Err for cam {cam_id}: {e}')
                    await asyncio.sleep(1 + retry)

            if not success:
                # Save the template URL anyway (may work without token)
                progress[cam_id] = {
                    'live_url': template,  # Just the template, may work
                    'template': template,
                    'fl_token': '',
                    'divas_token': '',
                    'sourceId': c.get('sourceId'),
                    'timestamp': time.time(),
                    'no_token': True,
                }
                n_fail += 1

            n_done += 1
            if n_done % 50 == 0:
                elapsed = time.time() - t0
                rate = n_done / max(elapsed, 1)
                log(f'  {n_done:,}/{len(to_query):,} ({n_success:,} ok, {n_fail:,} fail) {rate:.0f}/s')
                with open(PROGRESS, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, indent=2)
                last_save = time.time()

            await asyncio.sleep(0.4)  # Rate limit

        # Final save
        with open(PROGRESS, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        log(f'\n[DONE] {n_done:,} cams, {n_success:,} with divas token, {n_fail:,} fail')

        await browser.close()

    # Build CSV
    await build_csv(progress, cams)


async def build_csv(progress, cams):
    """Update master CSV with fl511 live URLs."""
    log('\n[BUILD] Updating master CSV...')

    # Build map: fl511 location -> live_url
    # We match by location string
    live_by_location = {}
    for c in cams:
        loc = c.get('location', '').strip()
        if not loc:
            continue
        cid = str(c['cam_id'])
        if cid in progress:
            live_by_location[loc] = progress[cid].get('live_url', '')

    log(f'  {len(live_by_location):,} locations with live URLs')

    csv.field_size_limit(2**31 - 1)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames

    fl511_rows = [(i, r) for i, r in enumerate(rows) if (r.get('host', '') or '').lower() == 'fl511.com']
    log(f'  {len(fl511_rows):,} fl511 rows in CSV')

    n_updated = 0
    n_no_match = 0
    unmatched_sample = []
    for i, row in fl511_rows:
        # Try matching by description, title, notes
        desc = (row.get('description', '') or '').strip()
        title = (row.get('page_title', '') or '').strip()
        notes = row.get('notes', '') or ''

        match = None
        for key in (desc, title):
            if key and key in live_by_location:
                match = live_by_location[key]
                break

        if not match:
            # Try to match by partial text in notes or title
            for loc, url in live_by_location.items():
                if not url:
                    continue
                if loc and (loc in desc or loc in title or loc in notes):
                    match = url
                    break

        if match:
            rows[i]['live_stream_url'] = match
            rows[i]['url'] = match
            rows[i]['type'] = 'video-hls'
            rows[i]['notes'] = (rows[i].get('notes', '') or '') + f' | fl511_live'
            n_updated += 1
        else:
            n_no_match += 1
            if len(unmatched_sample) < 5:
                unmatched_sample.append((i, desc, title))

    log(f'  Updated {n_updated} of {len(fl511_rows)} rows', flush=True)
    log(f'  {n_no_match} did not match', flush=True)
    if unmatched_sample:
        log('Sample unmatched:')
        for i, d, t in unmatched_sample:
            log(f'  [{i}] desc="{d[:60]}" title="{t[:60]}"', flush=True)

    # Save
    tmp = CSV_PATH + '.tmp'
    for attempt in range(20):
        try:
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                w.writerows(rows)
            os.replace(tmp, CSV_PATH)
            log(f'  Saved CSV with {n_updated} fl511 rows updated', flush=True)
            return
        except PermissionError:
            time.sleep(2 + random.uniform(0, 3))
    log('  ERROR: Could not save CSV', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
