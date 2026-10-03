"""Get all 4,871 fl511 cameras with full data using Playwright."""
import asyncio
import json
import time
from playwright.async_api import async_playwright

URL_TPL = 'https://fl511.com/List/GetData/Cameras?query=%7B%22columns%22%3A%5B%7B%22data%22%3Anull%2C%22name%22%3A%22%22%7D%2C%7B%22name%22%3A%22sortOrder%22%2C%22s%22%3Atrue%7D%2C%7B%22name%22%3A%22region%22%2C%22s%22%3Atrue%7D%2C%7B%22name%22%3A%22county%22%2C%22s%22%3Atrue%7D%2C%7B%22name%22%3A%22roadway%22%2C%22s%22%3Atrue%7D%2C%7B%22name%22%3A%22location%22%7D%2C%7B%22name%22%3A%22direction%22%2C%22s%22%3Atrue%7D%2C%7B%22data%22%3A7%2C%22name%22%3A%22%22%7D%5D%2C%22order%22%3A%5B%7B%22column%22%3A1%2C%22dir%22%3A%22asc%22%7D%2C%7B%22column%22%3A2%2C%22dir%22%3A%22asc%22%7D%5D%2C%22start%22%3A{START}%2C%22length%22%3A{LENGTH}%2C%22search%22%3A%7B%22value%22%3A%22%22%7D%7D&lang=en'


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to get session
        print('[1] Getting session...', flush=True)
        try:
            await page.goto('https://fl511.com/cctv', wait_until='domcontentloaded', timeout=60000)
        except:
            pass
        await asyncio.sleep(30)
        print(f'  URL: {page.url}', flush=True)

        # Get the token from page
        token = await page.evaluate('''() => {
            const meta = document.querySelector('input[name="__RequestVerificationToken"]');
            return meta ? meta.value : null;
        }''')
        print(f'  Token: {token[:50] if token else "NOT FOUND"}...', flush=True)

        # Get cookies
        cookies = await page.context.cookies()
        cookie_str = '; '.join([f'{c["name"]}={c["value"]}' for c in cookies])
        print(f'  Cookies ({len(cookies)}): {cookie_str[:200]}...', flush=True)

        # Now use the page's fetch to get all data
        print('\n[2] Fetching all cameras via page fetch...', flush=True)
        all_data = await page.evaluate('''async (args) => {
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
            if (!r.ok) return { error: r.status, text: await r.text() };
            return await r.json();
        }''', {'start': 0, 'length': 10, 'token': token or ''})
        print(f'  Status: {type(all_data).__name__}', flush=True)
        if isinstance(all_data, dict) and 'data' in all_data:
            print(f'  Total: {all_data.get("recordsTotal")}', flush=True)
            print(f'  Returned: {len(all_data.get("data", []))}', flush=True)
            print(f'  First cam: {json.dumps(all_data["data"][0], indent=2)[:1500]}', flush=True)

            # Save first 10
            with open('fl511_cams_10.json', 'w') as f:
                json.dump(all_data, f, indent=2)
            print(f'  Saved to fl511_cams_10.json', flush=True)

            # Now fetch ALL in batches
            total = all_data.get('recordsTotal', 0)
            print(f'\n[3] Fetching all {total} cams in batches of 100...', flush=True)
            all_cams = list(all_data.get('data', []))

            # Load existing progress if any
            import os
            if os.path.exists('fl511_cams_all.json'):
                with open('fl511_cams_all.json') as f:
                    prev = json.load(f)
                existing_cams = prev.get('cams', [])
                # Find max id we've seen
                if existing_cams:
                    max_id = max(c.get('id', 0) for c in existing_cams)
                    print(f'  Resuming from previous run with {len(existing_cams)} cams, max id={max_id}', flush=True)
                    all_cams = existing_cams
                    # Start after the highest id
                    skip_until = max_id
                else:
                    skip_until = 0
            else:
                skip_until = 0

            for offset in range(0, total, 50):
                # Skip if we've already fetched this batch
                batch_ids = [c.get('id') for c in all_cams]
                if batch_ids and max(batch_ids) >= offset + 50:
                    continue

                success = False
                for retry in range(3):
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
                            if (!r.ok) return { error: r.status, text: await r.text() };
                            return await r.json();
                        }''', {'start': offset, 'length': 50, 'token': token or ''})
                        if isinstance(batch, dict) and 'data' in batch:
                            all_cams.extend(batch.get('data', []))
                            success = True
                            break
                        elif isinstance(batch, dict) and 'error' in batch:
                            print(f'  Retry {retry+1}/3 at offset {offset}: err {batch["error"]}', flush=True)
                            await asyncio.sleep(2 ** retry)
                    except Exception as e:
                        print(f'  Retry {retry+1}/3 at offset {offset}: {e}', flush=True)
                        await asyncio.sleep(2 ** retry)

                if not success:
                    print(f'  Giving up at offset {offset}', flush=True)
                    # Save progress
                    with open('fl511_cams_all.json', 'w') as f:
                        json.dump({'cams': all_cams, 'total': total}, f)
                    break

                if len(all_cams) % 200 == 0 or offset % 500 == 0:
                    print(f'  {len(all_cams)}/{total} cams (offset {offset})', flush=True)
                    with open('fl511_cams_all.json', 'w') as f:
                        json.dump({'cams': all_cams, 'total': total}, f)

                await asyncio.sleep(0.5)  # Rate limit

            print(f'\n[FINAL] {len(all_cams)} cams fetched', flush=True)
            with open('fl511_cams_all.json', 'w') as f:
                json.dump({'cams': all_cams, 'total': total}, f, indent=2)
            print(f'  Saved to fl511_cams_all.json', flush=True)
        else:
            print(f'  Result: {all_data}', flush=True)

        await browser.close()

asyncio.run(main())
