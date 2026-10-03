"""Fast direct API calls to fl511 + divas (no browser, parallelized).

Rate-limit aware: 30 req/min on fl511 = 1 every 2s.
"""
import asyncio
import csv
import json
import os
import re
import time
import random
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import http.cookiejar

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
FL511_DATA = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_cams_with_live.json'
PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_divas_full_tokens.json'
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


def get_fl_token(image_id, cookies, token, retries=2):
    """Get fl511 token for imageId."""
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
                time.sleep(3 + retry * 3)
                continue
            return {'error': e.code}
        except Exception as e:
            time.sleep(2 + retry)
    return {'error': 'max_retries'}


def get_divas_token(body, cookies, token, retries=2):
    """Get divas secure token."""
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
                time.sleep(3 + retry * 3)
                continue
            return None
        except Exception as e:
            time.sleep(2 + retry)
    return None


def get_session():
    """Get fl511 session and token via direct HTTP calls. Returns (cookies_str, token) tuple."""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))

    # Step 1: GET /cctv to get cookies + token
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

    # Extract CSRF token from HTML
    m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html)
    if not m:
        m = re.search(r'antiForgeryToken["\']\s*:\s*["\']([^"\']+)', html)
    if not m:
        log(f'No token in HTML, found {len(cj)} cookies')
        return None, None

    token = m.group(1)
    cookie_str = '; '.join(f'{c.name}={c.value}' for c in cj)
    return cookie_str, token


class SessionPool:
    """Pool of sessions that auto-refresh on 429."""

    def __init__(self, n_sessions=8):
        self.n_sessions = n_sessions
        self.sessions = []
        self.locks = []
        self.idx = 0
        for _ in range(n_sessions):
            self.locks.append(None)
        # Initial populate
        for i in range(n_sessions):
            s = self._new_session()
            self.sessions.append(s)
            if i < n_sessions - 1:
                time.sleep(0.3)

    def _new_session(self):
        cookie_str, token = get_session()
        if not (cookie_str and token):
            return None
        return {'cookies': cookie_str, 'token': token, 'errors': 0}

    def get(self):
        """Get a session in round-robin, skipping dead ones."""
        for _ in range(self.n_sessions * 2):
            with_session = self.sessions[self.idx % self.n_sessions]
            self.idx += 1
            if with_session is not None:
                return with_session, self.idx % self.n_sessions
        return None, -1

    def invalidate(self, idx):
        """Mark a session as dead (needs refresh)."""
        if 0 <= idx < self.n_sessions:
            log(f'  Invalidating session {idx}, will refresh')
            self.sessions[idx] = None
            # Refresh after a delay
            time.sleep(5)
            new = self._new_session()
            if new:
                self.sessions[idx] = new
                log(f'  Refreshed session {idx}')


def process_cam(cam_data, cookies, token):
    """Process one cam: get fl_token then divas token, return full URL."""
    cam_id = str(cam_data['cam_id'])
    image_id = cam_data.get('image_id')
    template = cam_data.get('video_url_template', '')
    if not image_id or not template:
        return cam_id, template, None

    # Get fl511 token
    fl_result = get_fl_token(image_id, cookies, token, retries=2)
    if not fl_result or 'error' in fl_result or 'token' not in fl_result:
        return cam_id, template, None

    # Get divas token (send FULL response, not just token field)
    divas_token = get_divas_token(fl_result, cookies, token, retries=2)
    if divas_token:
        sep = '&' if '?' in template else '?'
        full_url = f'{template}{sep}token={divas_token}'
        return cam_id, full_url, divas_token

    return cam_id, template, None


def main():
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
        build_csv(progress, cams)
        return

    # Get N sessions (one per worker)
    n_sessions = 6
    sessions = []
    log(f'Getting {n_sessions} sessions...')
    for i in range(n_sessions):
        cookie_str, token = get_session()
        if cookie_str and token:
            sessions.append((cookie_str, token))
            log(f'  Session {i+1}: {token[:20]}...')
        else:
            log(f'  Session {i+1} failed')
        time.sleep(0.5)  # Don't hammer
    if not sessions:
        log('FATAL: No sessions')
        return

    # Process in parallel - use multiple sessions round-robin
    t0 = time.time()
    n_done = 0
    n_success = 0
    n_fail = 0
    last_save = time.time()

    session_lock = [0]  # round-robin index

    def process_with_session(c):
        # Round-robin session assignment
        idx = session_lock[0] % len(sessions)
        session_lock[0] += 1
        cookie_str, token = sessions[idx]
        return process_cam(c, cookie_str, token)

    with ThreadPoolExecutor(max_workers=len(sessions)) as ex:
        futures = {ex.submit(process_with_session, c): c for c in to_query}
        for f in as_completed(futures):
            cam_id, live_url, divas_token = f.result()
            if live_url and divas_token:
                progress[cam_id] = {
                    'live_url': live_url,
                    'divas_token': divas_token,
                    'timestamp': time.time(),
                }
                n_success += 1
            else:
                # Save template as fallback
                cam = next((c for c in to_query if str(c['cam_id']) == cam_id), None)
                if cam:
                    progress[cam_id] = {
                        'live_url': cam.get('video_url_template', ''),
                        'no_token': True,
                        'timestamp': time.time(),
                    }
                n_fail += 1

            n_done += 1
            if n_done % 50 == 0:
                elapsed = time.time() - t0
                rate = n_done / max(elapsed, 1)
                log(f'  {n_done:,}/{len(to_query):,} ({n_success:,} ok, {n_fail:,} fail) {rate:.1f}/s')
                with open(PROGRESS, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, indent=2)
                last_save = time.time()

        # Final save
        with open(PROGRESS, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        elapsed = time.time() - t0
        log(f'\n[DONE] {n_done:,} cams, {n_success:,} with divas token, {n_fail:,} fail, in {elapsed:.0f}s')

    # Build CSV
    build_csv(progress, cams)


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
    main()
