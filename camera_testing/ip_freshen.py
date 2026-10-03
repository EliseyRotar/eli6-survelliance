"""Tier 4: IP-API.com freshener.

For each unique IP that appears in the CSV, query ip-api.com (45 req/min rate limit)
to get fresher lat/lon/city/region/zip/isp/org/as/reverse.

Use batch endpoint to query up to 100 IPs per request when possible.
"""
import csv
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\ipfresh_log.txt'
CACHE_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\backups\ipapi_cache.json'


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=1)


def query_batch(ips, s):
    """Query ip-api batch endpoint. Returns dict ip -> info."""
    if not ips:
        return {}
    url = 'http://ip-api.com/batch'
    fields = 'status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,reverse,mobile,proxy,hosting,query'
    try:
        r = s.post(url, json=ips, params={'fields': fields}, timeout=20)
        if r.status_code == 429:
            log('  rate limited, waiting 60s')
            time.sleep(60)
            return {}
        if r.status_code != 200:
            log(f'  HTTP {r.status_code}: {r.text[:100]}')
            return {}
        return {info.get('query', ''): info for info in r.json()}
    except Exception as e:
        log(f'  batch err: {e}')
        return {}


def main():
    log('[init] starting IP-API freshener (Tier 4)')
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries))
    s.headers.update({'User-Agent': 'eli6-surveillance/1.0'})

    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    log(f'[init] {len(rows)-1} rows')

    cols = {h: i for i, h in enumerate(header)}
    HOST = cols['host']
    LAT = cols['lat']; LON = cols['lon']
    CCY = cols['country']; CREG = cols['region']; CCI = cols['city']
    CZIP = cols.get('zip', None)
    CADDR = cols.get('address', None)
    CISP = cols['isp']; CORG = cols['org']; CASN = cols['asn']
    CREV = cols['reverse_dns']
    CGEO = cols.get('geo_source', None)

    # Find unique IPs in host column
    unique_ips = set()
    for r in rows[1:]:
        h = r[HOST].strip() if len(r) > HOST else ''
        # Match IPv4 pattern
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', h):
            unique_ips.add(h)
    log(f'[plan] {len(unique_ips)} unique IPs')

    cache = load_cache()
    log(f'[cache] {len(cache)} cached entries')
    to_query = [ip for ip in unique_ips if ip not in cache]
    log(f'[plan] {len(to_query)} IPs to query')

    # Process in batches of 100 (ip-api limit), 1 req every ~2 sec = 30/min < 45 limit
    batch_size = 100
    for i in range(0, len(to_query), batch_size):
        batch = to_query[i:i+batch_size]
        result = query_batch(batch, s)
        for ip, info in result.items():
            cache[ip] = info
        save_cache(cache)
        log(f'  batch {i//batch_size+1}/{(len(to_query)+batch_size-1)//batch_size}, got {len(result)} results')
        time.sleep(3)  # rate limit: stay under 45/min

    log(f'[apply] updating CSV with cached IP info')
    updated = 0
    for r in rows[1:]:
        h = r[HOST].strip() if len(r) > HOST else ''
        if h not in cache:
            continue
        info = cache[h]
        if info.get('status') != 'success':
            continue
        changed = False
        # Update only if field is empty or significantly worse than new
        if info.get('lat') is not None and info.get('lon') is not None:
            try:
                new_lat = float(info['lat']); new_lon = float(info['lon'])
                if r[LAT]:
                    try:
                        old_lat = float(r[LAT])
                        # Only update if old is from IP-API (geo_source starts with tier4 or 'ipapi')
                        if CGEO is not None and len(r) > CGEO and r[CGEO].startswith(('tier4', 'ipapi')):
                            r[LAT] = str(new_lat); r[LON] = str(new_lon); changed = True
                    except ValueError:
                        r[LAT] = str(new_lat); r[LON] = str(new_lon); changed = True
                else:
                    r[LAT] = str(new_lat); r[LON] = str(new_lon); changed = True
            except (ValueError, TypeError):
                pass
        if info.get('city') and (not r[CCI] or len(r[CCI]) < len(info['city'])):
            r[CCI] = info['city'][:80]; changed = True
        if info.get('regionName') and (not r[CREG] or len(r[CREG]) < len(info['regionName'])):
            r[CREG] = info['regionName'][:80]; changed = True
        if info.get('country') and (not r[CCY] or len(r[CCY]) < len(info['country'])):
            r[CCY] = info['country']; changed = True
        if info.get('zip') and CZIP is not None and not r[CZIP]:
            r[CZIP] = str(info['zip']); changed = True
        if info.get('isp') and not r[CISP]:
            r[CISP] = info['isp'][:80]; changed = True
        if info.get('org') and not r[CORG]:
            r[CORG] = info['org'][:80]; changed = True
        if info.get('as') and not r[CASN]:
            r[CASN] = info['as'][:80]; changed = True
        if info.get('reverse') and not r[CREV]:
            r[CREV] = info['reverse'][:80]; changed = True
        if changed:
            if CGEO is not None:
                if not r[CGEO]:
                    r[CGEO] = 'tier4:ipapi'
                elif 'tier4' not in r[CGEO]:
                    r[CGEO] = (r[CGEO] + ',tier4:ipapi')[:200]
            elif 'geo_source' in cols:  # col exists but our col dict had wrong index
                # recompute: geo_source is column 26 (after we added address col 23)
                g_idx = cols['geo_source']
                if g_idx < len(r):
                    if not r[g_idx]:
                        r[g_idx] = 'tier4:ipapi'
                    elif 'tier4' not in r[g_idx]:
                        r[g_idx] = (r[g_idx] + ',tier4:ipapi')[:200]
            updated += 1

    log(f'[done] updated {updated} rows')
    tmp = CSV_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow(r)
    os.replace(tmp, CSV_PATH)


if __name__ == '__main__':
    main()
