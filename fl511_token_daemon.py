"""FL511 token refresh daemon.

Continuously refreshes tokens for known cams. Writes to:
- SQLite DB (for fast queries)
- JSON file (for backwards compat with existing scripts)
"""
import csv
import json
import os
import re
import sys
import time
import threading
import http.cookiejar
import urllib.request
import ssl
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import shared helpers from fl511_helpers.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl511_helpers as flh

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

WORK_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
FL511_CAMS = os.path.join(WORK_DIR, 'fl511_cams_with_live.json')
TOKENS_JSON = os.path.join(WORK_DIR, 'fl511_divas_full_tokens.json')
TOKENS_DB = os.path.join(WORK_DIR, 'camera_testing', 'fl511_tokens.db')

PID_FILE = os.path.join(WORK_DIR, 'fl511_token_daemon.pid')
LOCK_PATH = WORK_DIR + '.lock'  # Don't actually lock CSV; just a marker
N_SESSIONS = 1  # single session to avoid fl511 rate limit


def log(msg):
    ts = time.strftime('%H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


def pid_alive():
    """Check if another daemon instance is running."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            import psutil
            if psutil.pid_exists(old_pid):
                proc = psutil.Process(old_pid)
                cmd = ' '.join(proc.cmdline() or [])
                if 'fl511_token_daemon' in cmd:
                    return True
        except Exception:
            pass
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
    # Write our pid
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    return False


def init_db():
    """Create SQLite DB if needed."""
    os.makedirs(os.path.dirname(TOKENS_DB), exist_ok=True)
    conn = sqlite3.connect(TOKENS_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tokens (
        cam_id TEXT PRIMARY KEY,
        source_id TEXT,
        system_source_id TEXT,
        live_url TEXT,
        divas_token TEXT,
        timestamp REAL,
        expires_at REAL,
        last_refresh_status TEXT
    )''')
    c.execute('CREATE INDEX IF NOT EXISTS ts_idx ON tokens(timestamp)')
    conn.commit()
    conn.close()


def save_token_db(cam_id, source_id, system_source_id, live_url, divas_token):
    """Persist a token to SQLite."""
    conn = sqlite3.connect(TOKENS_DB, timeout=10)
    c = conn.cursor()
    now = time.time()
    # Tokens expire after 5 min; refresh before then
    expires = now + 240
    c.execute('''INSERT OR REPLACE INTO tokens
        (cam_id, source_id, system_source_id, live_url, divas_token, timestamp, expires_at, last_refresh_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (str(cam_id), str(source_id), str(system_source_id), live_url, divas_token, now, expires, 'ok'))
    conn.commit()
    conn.close()


def load_json_tokens():
    try:
        with open(TOKENS_JSON) as f:
            return json.load(f)
    except Exception:
        return {}


def save_json_tokens(tokens):
    """Save tokens to JSON (backwards compat)."""
    tmp = TOKENS_JSON + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, indent=2)
    os.replace(tmp, TOKENS_JSON)


# ---------------------------------------------------------------------------
# fl511 session/token
# ---------------------------------------------------------------------------
def get_fl_session():
    try:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj),
            urllib.request.HTTPSHandler(context=ctx),
        )
        req = urllib.request.Request('https://fl511.com/cctv', headers={
            'User-Agent': 'Mozilla/5.0',
        })
        with opener.open(req, timeout=15) as r:
            html = r.read().decode('utf-8', errors='replace')
        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html)
        if not m:
            return None, None
        token = m.group(1)
        cookie_str = '; '.join(f'{c.name}={c.value}' for c in cj)
        return cookie_str, token
    except Exception as e:
        return None, None


def get_divas_token(cam, session, retries=1, prefer_host=None):
    """Get divas token for one cam. Returns (live_url, divas_token, source_id, sys_source) or Nones."""
    cam_id = str(cam['cam_id'])
    image_id = cam.get('image_id')
    if not image_id:
        return None, None, None, None
    return flh.get_divas_token_for_cam(image_id, session, prefer_host=prefer_host)


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
def worker(cam, sessions, idx_lock, idx_counter, existing_tokens=None):
    """Refresh one cam's token. Returns (cam_id, url, divas_token, source_id, sys_source, ts)."""
    cam_id = str(cam['cam_id'])
    with idx_lock:
        # Pick best session (fewest errors)
        valid = [s for s in sessions if s is not None and s['errors'] < 5]
        if not valid:
            return cam_id, None, None, None, None, None
        s = min(valid, key=lambda x: x['errors'])
    # Determine prefer_host from existing cached URL (preserve discovered host) or fall back to CSV lookup
    prefer_host = None
    cached = (existing_tokens or {}).get(cam_id)
    if cached:
        cached_url = cached.get('live_url', '')
        m = re.search(r'(https?://dis-se\d+\.divas\.cloud:8200)', cached_url)
        if m:
            prefer_host = m.group(1)
    if not prefer_host:
        try:
            prefer_host = flh.build_host_for_chan(int(cam_id))
        except Exception:
            prefer_host = None
    result = get_divas_token(cam, s, prefer_host=prefer_host)
    if result and result[0]:
        url, token, source_id, sys_source = result
        return cam_id, url, token, source_id, sys_source, time.time()
    return cam_id, None, None, None, None, None


def refresh_sessions(sessions):
    """Refresh sessions with too many errors."""
    for i, s in enumerate(sessions):
        if s is None or s['errors'] >= 5:
            log(f'  Refreshing session {i}...')
            time.sleep(1)
            c, t = get_fl_session()
            if c and t:
                sessions[i] = {'cookies': c, 'token': t, 'errors': 0, 'created': time.time()}
                log(f'  Session {i} refreshed')
            else:
                log(f'  Session {i} refresh failed')


def main():
    sys.stdout.reconfigure(line_buffering=True)
    if pid_alive():
        log('Another daemon already running, exiting')
        return

    init_db()

    # Load cams
    with open(FL511_CAMS) as f:
        cams = json.load(f)
    cams = [c for c in cams if c.get('video_url_template') and c.get('image_id')]
    log(f'Loaded {len(cams):,} cams with templates')

    # Load existing tokens
    tokens = load_json_tokens()
    log(f'Loaded {len(tokens):,} existing tokens')

    # Session pool
    sessions = []
    log(f'Getting {N_SESSIONS} sessions...')
    for i in range(N_SESSIONS):
        c, t = get_fl_session()
        if c and t:
            sessions.append({'cookies': c, 'token': t, 'errors': 0, 'created': time.time()})
            log(f'  Session {i+1}: {t[:20]}...')
        else:
            sessions.append(None)
            log(f'  Session {i+1} failed')
        time.sleep(0.3)

    if not any(sessions):
        log('FATAL: No sessions')
        return

    idx_lock = threading.Lock()
    idx_counter = [0]

    cycle = 0
    while True:
        cycle += 1
        now = time.time()
        # Find cams that need token refresh (older than 4 min)
        need_refresh = []
        for c in cams:
            cid = str(c['cam_id'])
            ts = tokens.get(cid, {}).get('timestamp', 0)
            if now - ts > 240:  # 4 min
                need_refresh.append(c)
        # Also include cams with no token
        for c in cams:
            cid = str(c['cam_id'])
            if cid not in tokens:
                if c not in need_refresh:
                    need_refresh.append(c)
        # Limit per cycle
        need_refresh = need_refresh[:300]  # smaller batches, less aggressive
        log(f'  [Cycle {cycle}] Refreshing {len(need_refresh):,} tokens')

        if not need_refresh:
            log(f'  [Cycle {cycle}] All fresh, sleeping 60s')
            time.sleep(60)
            continue

        # Refresh sessions with errors
        refresh_sessions(sessions)

        t0 = time.time()
        n_done = 0
        n_success = 0
        n_fail = 0
        batch = {}

        with ThreadPoolExecutor(max_workers=N_SESSIONS) as ex:
            futs = {ex.submit(worker, c, sessions, idx_lock, idx_counter, tokens): c for c in need_refresh}
            for f in as_completed(futs):
                cam = futs[f]
                try:
                    cam_id, url, token, source_id, sys_source, ts = f.result()
                except Exception as e:
                    n_fail += 1
                    continue
                n_done += 1
                # Refresh sessions with errors
                for si, s in enumerate(sessions):
                    if s and s['errors'] >= 5:
                        refresh_sessions(sessions)
                        break
                if url and token:
                    n_success += 1
                    batch[cam_id] = {
                        'live_url': url,
                        'divas_token': token,
                        'sourceId': source_id,
                        'systemSourceId': sys_source,
                        'timestamp': ts,
                    }
                    save_token_db(cam_id, source_id, sys_source, url, token)
                else:
                    n_fail += 1
                if n_done % 50 == 0:
                    elapsed = time.time() - t0
                    rate = n_done / max(elapsed, 1)
                    active = sum(1 for s in sessions if s and s['errors'] < 5)
                    log(f'  {n_done:,}/{len(need_refresh):,} ({n_success:,} ok, {n_fail:,} fail) {rate:.1f}/s, {active}/{N_SESSIONS} sessions active')

        # Merge into tokens dict and save JSON
        tokens.update(batch)
        save_json_tokens(tokens)
        elapsed = time.time() - t0
        log(f'\n[Cycle {cycle}] {n_done:,} cams, {n_success:,} tokens refreshed, {n_fail:,} fail, in {elapsed:.0f}s')

        # Loop back
        log(f'  [Cycle {cycle}] Sleeping 30s before next cycle')
        time.sleep(30)


if __name__ == '__main__':
    try:
        main()
    finally:
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
