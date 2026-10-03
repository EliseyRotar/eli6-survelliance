"""Get all 4,871 fl511 cams with better retry logic + resume support."""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

PAGE_URL = 'https://fl511.com/cctv'
LIST_URL = 'https://fl511.com/List/GetData/Cameras'
OUT_FILE = 'fl511_cams_all.json'


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Load existing progress
        all_cams = []
        existing_ids = set()
        if os.path.exists(OUT_FILE):
            try:
                with open(OUT_FILE) as f:
                    prev = json.load(f)
                all_cams = prev.get('cams', [])
                existing_ids = {c.get('id') for c in all_cams if c.get('id')}
                print(f'[RESUME] Loaded {len(all_cams):,} cams, {len(existing_ids):,} unique IDs', flush=True)
            except Exception as e:
                print(f'[RESUME] err: {e}', flush=True)

        # Navigate to get session
        print('[1] Getting session...', flush=True)
        try:
            await page.goto(PAGE_URL, wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(f'  goto err: {e}', flush=True)
        await asyncio.sleep(30)
        print(f'  URL: {page.url}', flush=True)

        # Get token
        token = await page.evaluate('''() => {
            const meta = document.querySelector('input[name="__RequestVerificationToken"]');
            return meta ? meta.value : null;
        }''')
        if not token:
            print('  FATAL: no token found', flush=True)
            await browser.close()
            return
        print(f'  Token: {token[:50]}...', flush=True)

        # Fetch all
        print(f'\n[2] Fetching all 4,871 cams in batches of 50...', flush=True)
        t0 = time.time()
        total_target = 4871
        batch_size = 50
        last_save = time.time()
        errors = 0

        for offset in range(0, total_target, batch_size):
            # Skip if this batch already loaded
            batch_ids = [c.get('id') for c in all_cams[offset:offset+batch_size] if c.get('id')]
            if len(batch_ids) == batch_size and all(b is not None for b in batch_ids):
                # Already have this batch
                continue

            success = False
            for retry in range(5):
                try:
                    batch = await page.evaluate('''async (args) => {
                        const { start, length, token } = args;
                        const url = `https://fl511.com/List/GetData/Cameras?query=` + encodeURIComponent(JSON.stringify({
                            "columns": [
                                {"data": null, "name": ""},
                                {"name": "sortOrder", "s": true},
                                {"name": "region", "s": true},
                                {"name": "county", "s": true},
                                {"name": "roadway", "s": true},
                                {"name": "location"},
                                {"name": "direction", "s": true},
                                {"data": 7, "name": ""}
                            ],
                            "order": [{"column": 1, "dir": "asc"}, {"column": 2, "dir": "asc"}],
                            "start": start,
                            "length": length,
                            "search": {"value": ""}
                        })) + '&lang=en';
                        const r = await fetch(url, {
                            headers: {
                                'Accept': 'application/json, text/javascript, */*; q=0.01',
                                'X-Requested-With': 'XMLHttpRequest',
                                '__RequestVerificationToken': token,
                            }
                        });
                        if (!r.ok) return { error: r.status, text: await r.text().catch(()=>'') };
                        return await r.json();
                    }''', {'start': offset, 'length': batch_size, 'token': token})
                    if isinstance(batch, dict) and 'data' in batch:
                        new_data = batch.get('data', [])
                        # Replace or append
                        for i, new_cam in enumerate(new_data):
                            if offset + i < len(all_cams):
                                all_cams[offset + i] = new_cam
                            else:
                                all_cams.append(new_cam)
                        success = True
                        break
                    elif isinstance(batch, dict) and 'error' in batch:
                        print(f'  Retry {retry+1}/5 at offset {offset}: err {batch["error"]}', flush=True)
                        await asyncio.sleep(2 ** retry)
                except Exception as e:
                    print(f'  Retry {retry+1}/5 at offset {offset}: {e}', flush=True)
                    await asyncio.sleep(2 ** retry)

            if not success:
                errors += 1
                print(f'  GIVING UP at offset {offset} (errors so far: {errors})', flush=True)
                if errors >= 3:
                    print(f'  Too many errors, stopping', flush=True)
                    break
                # Try to refresh session
                try:
                    await page.reload(wait_until='domcontentloaded', timeout=60000)
                    await asyncio.sleep(20)
                    token = await page.evaluate('''() => {
                        const meta = document.querySelector('input[name="__RequestVerificationToken"]');
                        return meta ? meta.value : null;
                    }''')
                    print(f'  Refreshed session, new token: {token[:30] if token else "None"}...', flush=True)
                except:
                    pass
            else:
                errors = 0  # Reset

            if offset % 200 == 0 or len(all_cams) % 200 == 0:
                elapsed = time.time() - t0
                rate = len(all_cams) / max(elapsed, 1)
                print(f'  {len(all_cams):,}/{total_target:,} cams (offset {offset}, {rate:.0f}/s)', flush=True)

            # Save progress every 30s
            if time.time() - last_save > 30:
                with open(OUT_FILE, 'w') as f:
                    json.dump({'cams': all_cams, 'total': total_target}, f)
                last_save = time.time()

            await asyncio.sleep(0.5)  # Rate limit

        # Final save
        elapsed = time.time() - t0
        with open(OUT_FILE, 'w') as f:
            json.dump({'cams': all_cams, 'total': total_target}, f)
        print(f'\n[FINAL] {len(all_cams):,} cams fetched in {elapsed:.0f}s', flush=True)
        print(f'  Saved to {OUT_FILE}', flush=True)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
