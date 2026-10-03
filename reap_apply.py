"""Apply reaper results to CSV - move dead cams to a quarantine file.

For each cam in reap_results.json:
- If dead: move to dead_cams_quarantine.csv
- If alive: keep in main CSV, update http_status, content_type
"""
import csv
import os
import json
import time
import re
import random
from collections import Counter

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
REAP = r'C:\Users\eli6-admin\Documents\eli6-surveillance\reap_results.json'
DEAD_CSV = r'C:\Users\eli6-admin\Documents\eli6-surveillance\dead_cams_quarantine.csv'
LOG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\reap_apply.log'  # workaround for cp1252

AUTH_CODES = {401, 403, 407, 451}


def main():
    csv.field_size_limit(2**31 - 1)

    # Load reaper results
    if not os.path.exists(REAP):
        print(f'No {REAP}')
        return
    with open(REAP) as f:
        reap_data = json.load(f)
    print(f'Reaper has {len(reap_data):,} probes')

    # Build probe index by URL
    by_url = {}
    for k, v in reap_data.items():
        if len(v) == 5:
            status, ct, size, latency, url = v
        elif len(v) == 6:
            idx, status, ct, size, latency, url = v
        else:
            continue
        by_url[url] = (status, ct, size, latency)

    # Load CSV
    print('Loading CSV...', flush=True)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames
    print(f'  {len(rows):,} rows', flush=True)

    # Apply results
    n_alive = 0
    n_dead = 0
    n_unknown = 0
    dead_rows = []
    n_updated = 0

    for i, row in enumerate(rows):
        url = row.get('url', '') or ''
        lsurl = row.get('live_stream_url', '') or ''
        # Try URL first, then live_stream_url
        probe = by_url.get(url)
        if not probe and lsurl:
            probe = by_url.get(lsurl)
        if not probe:
            n_unknown += 1
            continue
        status, ct, size, latency = probe

        if status in AUTH_CODES:
            # Auth-required = still alive
            n_alive += 1
            rows[i]['live_status'] = 'auth_required'
            rows[i]['http_status'] = str(status)
            n_updated += 1
        elif status == 200 and size > 100:
            # Alive
            n_alive += 1
            # Update status
            rows[i]['live_status'] = 'live'
            rows[i]['http_status'] = '200'
            if ct and ct != rows[i].get('content_type', ''):
                rows[i]['content_type'] = ct
            n_updated += 1
        else:
            # divas.cloud / fl511 HLS: 401/403/429/500/503 = token expired, NOT dead
            if isinstance(url, str) and ('divas.cloud' in url.lower() or 'fl511.com' in url.lower()):
                if status in (401, 403, 429) or (500 <= status < 600):
                    n_alive += 1
                    rows[i]['live_status'] = 'live'  # still alive, token will be refreshed
                    rows[i]['http_status'] = str(status)
                    n_updated += 1
                    continue
                if status < 0:
                    # Network glitch on divas CDN — keep cam, don't kill
                    n_alive += 1
                    rows[i]['live_status'] = 'live'
                    rows[i]['http_status'] = str(status)
                    n_updated += 1
                    continue
            n_dead += 1
            rows[i]['live_status'] = 'dead'
            rows[i]['http_status'] = str(status)
            dead_rows.append(row)
            n_updated += 1
            if n_dead <= 3:
                print(f'  Marking dead: idx={rows[i].get("idx")} url={url[:60]} status={status}', flush=True)

    print(f'\n  Alive: {n_alive:,}', flush=True)
    print(f'  Dead: {n_dead:,}', flush=True)
    print(f'  Unknown: {n_unknown:,}', flush=True)
    print(f'  Updated: {n_updated:,}', flush=True)

    # Save dead cams to quarantine (append, dedup by URL)
    if dead_rows:
        existing_urls = set()
        existing = []
        if os.path.exists(DEAD_CSV):
            try:
                with open(DEAD_CSV, 'r', encoding='utf-8', errors='replace', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get('url', '')
                        if url and url not in existing_urls:
                            existing_urls.add(url)
                            existing.append(row)
            except Exception:
                pass
        # Add new dead rows
        new_count = 0
        for row in dead_rows:
            url = row.get('url', '')
            if url and url not in existing_urls:
                existing_urls.add(url)
                existing.append(row)
                new_count += 1
        # Write combined
        with open(DEAD_CSV, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            w.writerows(existing)
        print(f'  Saved {len(existing):,} dead cams ({new_count:,} new) to {DEAD_CSV}', flush=True)

    # Save updated CSV
    if n_updated > 0:
        tmp = CSV_PATH + '.tmp'
        # Clean up rows that have None or extra fields
        extra_fields = set()
        for row in rows:
            for k in list(row.keys()):
                if k is None or k not in header:
                    extra_fields.add(k)
        if extra_fields:
            for row in rows:
                for k in extra_fields:
                    row.pop(k, None)
        for attempt in range(20):
            try:
                with open(tmp, 'w', encoding='utf-8', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
                    w.writeheader()
                    w.writerows(rows)
                # Check if tmp exists
                tmp_size = os.path.getsize(tmp)
                print(f'  tmp size: {tmp_size:,} bytes', flush=True)
                os.replace(tmp, CSV_PATH)
                # Verify it was replaced
                csv_size = os.path.getsize(CSV_PATH)
                print(f'  CSV size after replace: {csv_size:,} bytes', flush=True)
                print(f'  Saved CSV with {n_updated:,} updated rows', flush=True)
                return
            except (PermissionError, OSError) as e:
                print(f'  retry {attempt}: {e}', flush=True)
                time.sleep(2 + random.uniform(0, 3))
        print('ERROR: Could not save CSV', flush=True)


if __name__ == '__main__':
    main()
