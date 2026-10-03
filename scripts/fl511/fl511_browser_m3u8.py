"""Use the browser to find m3u8 URLs for fl511 cams.

For each cam, navigate to its page, click Show Video, capture the m3u8 URL.
This is slow but reliable since the browser has full session.
"""
import asyncio
import json
import os
import re
import time
from playwright.async_api import async_playwright

FL511_DATA = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_cams_with_live.json'
PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_m3u8_urls.json'


async def main():
    # Load fl511 cams - just the ones with image_url
    with open(FL511_DATA, encoding='utf-8') as f:
        cams = json.load(f)
    cams = [c for c in cams if c.get('video_url_template')]
    print(f'Loaded {len(cams):,} cams with video templates', flush=True)

    # Load progress
    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS) as f:
                progress = json.load(f)
        except:
            pass
    print(f'  Already have {len(progress):,} m3u8 URLs', flush=True)

    to_query = [c for c in cams if str(c['cam_id']) not in progress]
    print(f'  Need to query: {len(to_query):,}', flush=True)

    if not to_query:
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # m3u8 URLs from browser network
        m3u8_urls = []

        async def on_response(resp):
            url = resp.url
            if '.m3u8' in url.lower() and 'dis-se' in url.lower():
                m3u8_urls.append({
                    'url': url,
                    'status': resp.status,
                })
        page.on('response', on_response)

        # Get fl511 session
        print('Going to fl511.com/cctv...', flush=True)
        try:
            await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(f'  err: {e}', flush=True)
        await asyncio.sleep(30)

        t0 = time.time()
        n_done = 0
        n_success = 0
        n_fail = 0

        # Get list of imageId -> DOM row id mapping
        for i, c in enumerate(to_query):
            cam_id = str(c['cam_id'])
            image_id = c.get('image_id')

            m3u8_urls.clear()
            try:
                # Navigate to the cam page (this is the iframe approach fl511 uses)
                # The URL is /map/Cctv/{id}?t={timestamp} - this returns the still image
                # But the live video is on /Cctv/{id}/view or similar
                # Or we can click on the cam in the list
                # Let's just open the cam directly via Show Video

                # Navigate to /cctv (already there)
                # Find the row with this image id and click Show Video
                # The image id is in the DT_RowId field

                # Use a direct approach - load /cctv/{id} or similar
                url = f'https://fl511.com/cctv/{image_id}'
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                except:
                    pass
                await asyncio.sleep(2)

                # Look for the live video link
                # Find the cam and click Show Video
                buttons = await page.query_selector_all('button')
                for b in buttons:
                    try:
                        text = await b.text_content()
                        if text and 'show video' in text.lower():
                            await b.click()
                            await asyncio.sleep(8)
                            break
                    except:
                        pass

                # Capture m3u8 URL from network
                if m3u8_urls:
                    m3u8 = m3u8_urls[0]['url']
                    if 'token=' not in m3u8:
                        # Need to get the token somehow
                        # The token is in the actual response
                        pass
                    progress[cam_id] = m3u8
                    n_success += 1
                else:
                    progress[cam_id] = None
                    n_fail += 1
            except Exception as e:
                print(f'  err for {cam_id}: {e}', flush=True)
                progress[cam_id] = None
                n_fail += 1

            n_done += 1
            if n_done % 10 == 0:
                elapsed = time.time() - t0
                rate = n_done / max(elapsed, 1)
                print(f'  {n_done}/{len(to_query)} ({n_success} ok, {n_fail} fail) {rate:.1f}/s', flush=True)
                with open(PROGRESS, 'w') as f:
                    json.dump(progress, f, indent=2)

            if n_done % 100 == 0:
                # Reload page to avoid stale state
                try:
                    await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=60000)
                    await asyncio.sleep(5)
                except:
                    pass

        # Final save
        with open(PROGRESS, 'w') as f:
            json.dump(progress, f, indent=2)
        elapsed = time.time() - t0
        print(f'\n[DONE] {n_done} cams, {n_success} with m3u8, in {elapsed:.0f}s', flush=True)

        await browser.close()


asyncio.run(main())
