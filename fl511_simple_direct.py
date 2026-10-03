"""Simple sequential fl511 direct API fetcher - one cam at a time.

Avoids file lock issues by writing only to its own file.
"""
import json
import os
import re
import time
import urllib.request
import ssl
import http.cookiejar

PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_divas_simple.json'
LOG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_divas_simple_log.txt'
FL511_DATA = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_cams_with_live.json'

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
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))
    req = urllib.request.Request('https://fl511.com/cctv', headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with opener.open(req, timeout=30) as r:
            html = r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None, None, str(e)
    m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html)
    if not m:
        return None, None, 'no token'
    token = m.group(1)
    cookie_str = '; '.join(f'{c.name}={c.value}' for c in cj)
    return opener, (cookie_str, token), 'ok'


def get_fl_token(opener, session, image_id):
    url = f'https://fl511.com/Camera/GetVideoUrl?imageId={image_id}&_={int(time.time()*1000)}'
    cookies, token = session
    for retry in range(3):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'X-Requested-With': 'XMLHttpRequest',
                '__RequestVerificationToken': token,
                'Cookie': cookies,
                'Referer': 'https://fl511.com/cctv',
            })
            with opener.open(req, timeout=10) as r:
                d = json.loads(r.read())
                if 'token' in d:
                    return d
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(3 + retry * 2)
                continue
            return None
        except Exception:
            time.sleep(2)
    return None


def get_divas_token(opener, session, body):
    cookies, token = session
    url = 'https://divas.cloud/VDS-API/SecureTokenUri/GetSecureTokenUriBySourceId'
    payload = json.dumps(body).encode()
    for retry in range(2):
        try:
            req = urllib.request.Request(url, data=payload, headers={
                'User-Agent': 'Mozilla/5.0',
                'Origin': 'https://fl511.com',
                'Referer': 'https://fl511.com/',
                'Content-Type': 'application/json',
                '__RequestVerificationToken': token,
                'Cookie': cookies,
            }, method='POST')
            with opener.open(req, timeout=10) as r:
                txt = r.read().decode()
                m = re.search(r'token=([A-Fa-f0-9]+)', txt)
                if m:
                    return m.group(1)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(3 + retry * 2)
                continue
            return None
        except Exception:
            time.sleep(2)
    return None


def main():
    # Load cams
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
    # Also load from main
    MAIN = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_divas_full_tokens.json'
    if os.path.exists(MAIN):
        try:
            with open(MAIN) as f:
                main = json.load(f)
            for k, v in main.items():
                if k not in progress and v.get('divas_token'):
                    progress[k] = v
        except:
            pass
    log(f'  {len(progress):,} already have full live URLs (merged)')

    to_query = [c for c in cams if str(c['cam_id']) not in progress]
    log(f'  Need to query: {len(to_query):,}')

    if not to_query:
        log('All done!')
        return

    # Get session
    log('Getting session...')
    opener, session, status = get_session()
    if not opener:
        log(f'FATAL: Could not get session: {status}')
        return
    log(f'  Session OK')

    t0 = time.time()
    n_done = 0
    n_success = 0
    n_fail = 0
    n_skipped = 0
    last_save = time.time()

    for c in to_query:
        cam_id = str(c['cam_id'])
        image_id = c.get('image_id')
        template = c.get('video_url_template', '')

        if not image_id or not template:
            continue
        if cam_id in progress and progress[cam_id].get('divas_token'):
            n_skipped += 1
            continue

        # Get fl511 token
        fl_result = get_fl_token(opener, session, image_id)
        if not fl_result:
            progress[cam_id] = {
                'live_url': template,
                'no_token': True,
                'timestamp': time.time(),
            }
            n_fail += 1
            n_done += 1
            continue

        # Get divas token
        divas_token = get_divas_token(opener, session, fl_result)
        if divas_token:
            sep = '&' if '?' in template else '?'
            full_url = f'{template}{sep}token={divas_token}'
            progress[cam_id] = {
                'live_url': full_url,
                'divas_token': divas_token,
                'fl_token': fl_result.get('token', ''),
                'timestamp': time.time(),
            }
            n_success += 1
        else:
            progress[cam_id] = {
                'live_url': template,
                'no_token': True,
                'timestamp': time.time(),
            }
            n_fail += 1

        n_done += 1
        if n_done % 20 == 0:
            elapsed = time.time() - t0
            rate = n_done / max(elapsed, 1)
            log(f'  {n_done:,}/{len(to_query):,} ({n_success:,} ok, {n_fail:,} fail) {rate:.2f}/s')
            tmp = PROGRESS + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(progress, f, indent=2)
            try:
                os.replace(tmp, PROGRESS)
            except OSError:
                pass
            last_save = time.time()

        # Rate limit: 1 req per 1.5s
        time.sleep(1.5)

    # Final save
    tmp = PROGRESS + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)
    try:
        os.replace(tmp, PROGRESS)
    except OSError:
        pass
    elapsed = time.time() - t0
    log(f'\n[DONE] {n_done:,} cams, {n_success:,} with divas token, {n_fail:,} fail, {n_skipped} skipped, in {elapsed:.0f}s')


if __name__ == '__main__':
    main()
