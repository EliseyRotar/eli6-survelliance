"""Fast direct API calls to fl511 + divas with session pool.

Rate-limit aware: 8 parallel sessions for higher throughput.
"""
import csv
import json
import os
import re
import time
import random
import urllib.request
import ssl
import http.cookiejar
import threading
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
FL511_DATA = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_cams_with_live.json'
PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_divas_full_tokens.json'
PROGRESS_DIRECT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_divas_direct.json'
LOG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\archive/logs\fl511_divas_full_log.txt'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass


def get_session():
    """Get fl511 session and token via direct HTTP calls."""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))
    req = urllib.request.Request('https://fl511.com/cctv', headers={
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'text/html',
    })
    try:
        with opener.open(req, timeout=30) as r:
            html = r.read().decode('utf-8', errors='replace')
    except Exception as e:
        log(f'Session err: {e}')
        return None, None
    m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html)
    if not m:
        m = re.search(r'antiForgeryToken["\']\s*:\s*["\']([^"\']+)', html)
    if not m:
        return None, None
    token = m.group(1)
    cookie_str = '; '.join(f'{c.name}={c.value}' for c in cj)
    return cookie_str, token


def get_fl_token(image_id, session, retries=1):
    """Get fl511 token for imageId."""
    cookies = session['cookies']
    token = session['token']
    url = f'https://fl511.com/Camera/GetVideoUrl?imageId={image_id}&_={int(time.time()*1000)}'
    for retry in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                '__RequestVerificationToken': token,
                'Cookie': cookies,
                'Referer': 'https://fl511.com/cctv',
                'Origin': 'https://fl511.com',
            })
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                body = r.read()
                d = json.loads(body)
                if 'token' in d:
                    return d
        except urllib.error.HTTPError as e:
            if e.code == 429:
                session['errors'] += 1
                time.sleep(3)
                continue
            return {'error': e.code}
        except Exception as e:
            time.sleep(2)
    return {'error': 'max_retries'}


def get_divas_token(body, session, retries=1):
    """Get divas secure token."""
    cookies = session['cookies']
    token = session['token']
    url = 'https://divas.cloud/VDS-API/SecureTokenUri/GetSecureTokenUriBySourceId'
    payload = json.dumps(body).encode()
    for retry in range(retries):
        try:
            req = urllib.request.Request(url, data=payload, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': '*/*',
                'Origin': 'https://fl511.com',
                'Referer': 'https://fl511.com/',
                'Content-Type': 'application/json',
                '__RequestVerificationToken': token,
                'Cookie': cookies,
            }, method='POST')
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                txt = r.read().decode()
                m = re.search(r'token=([A-Fa-f0-9]+)', txt)
                if m:
                    return m.group(1)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                session['errors'] += 1
                time.sleep(3)
                continue
            return None
        except Exception as e:
            time.sleep(2)
    return None


def process_cam(cam_data, sessions, idx_lock, idx_counter):
    """Process one cam using a session from the pool."""
    cam_id = str(cam_data['cam_id'])
    image_id = cam_data.get('image_id')
    template = cam_data.get('video_url_template', '')
    if not image_id or not template:
        return cam_id, template, None

    with idx_lock:
        idx = idx_counter[0] % len(sessions)
        idx_counter[0] += 1

    # Get a valid session
    session = None
    for _ in range(len(sessions) * 2):
        if sessions[idx] is not None and sessions[idx]['errors'] < 5:
            session = sessions[idx]
            break
        idx = (idx + 1) % len(sessions)
    if not session:
        return cam_id, template, None

    # Get fl511 token
    fl_result = get_fl_token(image_id, session, retries=1)
    if not fl_result or 'error' in fl_result or 'token' not in fl_result:
        return cam_id, template, None

    # Get divas token
    divas_token = get_divas_token(fl_result, session, retries=1)
    if divas_token:
        sep = '&' if '?' in template else '?'
        full_url = f'{template}{sep}token={divas_token}'
        return cam_id, full_url, divas_token

    return cam_id, template, None


def refresh_session(idx, sessions):
    """Refresh a rate-limited session."""
    if 0 <= idx < len(sessions):
        log(f'  Refreshing session {idx}...')
        time.sleep(3)
        c, t = get_session()
        if c and t:
            sessions[idx] = {'cookies': c, 'token': t, 'errors': 0}
            log(f'  Session {idx} refreshed')
        else:
            log(f'  Session {idx} refresh failed')


def main():
    # Load fl511 cams
    with open(FL511_DATA, encoding='utf-8') as f:
        cams = json.load(f)
    cams = [c for c in cams if c.get('video_url_template')]
    log(f'Loaded {len(cams):,} cams with templates')

    # Load progress from main file (shared with browser) + our own
    progress = {}
    for p in [PROGRESS, PROGRESS_DIRECT]:
        if os.path.exists(p):
            try:
                with open(p) as f:
                    d = json.load(f)
                for k, v in d.items():
                    if k not in progress or v.get('divas_token'):
                        progress[k] = v
            except:
                pass
    log(f'  {len(progress):,} already have full live URLs (combined)')

    # Loop forever - re-query expired tokens every 15 min
    cycle = 0
    while True:
        cycle += 1
        now = time.time()
        # Find expired tokens (>5 min old) or missing
        expired_ids = []
        for c in cams:
            cid = str(c['cam_id'])
            if cid not in progress:
                expired_ids.append(c)
            else:
                ts = progress[cid].get('timestamp', 0)
                if now - ts > 300:  # 5 min
                    expired_ids.append(c)

        # Limit to first 1000 per cycle
        to_query = expired_ids[:1000]
        log(f'  [Cycle {cycle}] Need to query: {len(to_query):,} (expired + new)')

        if not to_query:
            log(f'  [Cycle {cycle}] All done, sleeping 5 min...')
            time.sleep(300)
            continue

        # Get sessions
        n_sessions = 4
        sessions = []
        log(f'Getting {n_sessions} sessions...')
        for i in range(n_sessions):
            c, t = get_session()
            if c and t:
                sessions.append({'cookies': c, 'token': t, 'errors': 0})
                log(f'  Session {i+1}: {t[:20]}...')
            else:
                sessions.append(None)
                log(f'  Session {i+1} failed')
            time.sleep(0.3)

        if not any(sessions):
            log('FATAL: No sessions')
            time.sleep(60)
            continue

        t0 = time.time()
        n_done = 0
        n_success = 0
        n_fail = 0
        last_save = time.time()
        idx_lock = threading.Lock()
        idx_counter = [0]

        with ThreadPoolExecutor(max_workers=n_sessions) as ex:
            futures = {ex.submit(process_cam, c, sessions, idx_lock, idx_counter): c for c in to_query}
            log(f'  Submitted {len(futures):,} tasks to executor')
            completed = 0
            for f in as_completed(futures):
                try:
                    cam_id, live_url, divas_token = f.result()
                    completed += 1
                except Exception as e:
                    completed += 1
                    log(f'  process_cam exception: {e}')
                    continue
                if live_url and divas_token:
                    progress[cam_id] = {
                        'live_url': live_url,
                        'divas_token': divas_token,
                        'timestamp': time.time(),
                    }
                    n_success += 1
                else:
                    cam = next((c for c in to_query if str(c['cam_id']) == cam_id), None)
                    if cam:
                        progress[cam_id] = {
                            'live_url': cam.get('video_url_template', ''),
                            'no_token': True,
                            'timestamp': time.time(),
                        }
                    n_fail += 1

                n_done += 1
                # Periodically refresh sessions with too many errors
                for si, s in enumerate(sessions):
                    if s and s['errors'] >= 5:
                        refresh_session(si, sessions)

                if n_done % 50 == 0:
                    elapsed = time.time() - t0
                    rate = n_done / max(elapsed, 1)
                    active = sum(1 for s in sessions if s and s['errors'] < 5)
                    log(f'  {n_done:,}/{len(to_query):,} ({n_success:,} ok, {n_fail:,} fail) {rate:.1f}/s, {active}/{n_sessions} sessions active')
                    # Save only to OUR file
                    tmp = PROGRESS_DIRECT + '.tmp'
                    with open(tmp, 'w', encoding='utf-8') as f:
                        json.dump(progress, f, indent=2)
                    try:
                        os.replace(tmp, PROGRESS_DIRECT)
                    except OSError:
                        pass
                    last_save = time.time()

                time.sleep(0.2)  # Small delay

            # Final save to OUR file only
            tmp = PROGRESS_DIRECT + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(progress, f, indent=2)
            try:
                os.replace(tmp, PROGRESS_DIRECT)
            except OSError:
                pass
            elapsed = time.time() - t0
            log(f'\n[DONE] {n_done:,} cams, {n_success:,} with divas token, {n_fail:,} fail, in {elapsed:.0f}s')

        # Build CSV
        build_csv(progress, cams)

        # Loop back - next cycle will pick up more expired tokens
        log(f'  [Cycle {cycle}] Sleeping 60s before next cycle...')
        time.sleep(60)


def build_csv(progress, cams):
    """Update master CSV with full live URLs."""
    log('\n[BUILD] Updating master CSV...')

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
    main()
