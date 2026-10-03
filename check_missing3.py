"""Find truly unique TV cams - those NOT yet in CSV (by ID and by URL).

These are cams whose source URL isn't anywhere in CSV. Most are likely
landing pages that point to a website where the cam actually lives.
"""
import json
import csv
import re
import sys

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
MISSING_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\tv_missing.json'


def main():
    csv.field_size_limit(2**31 - 1)

    with open(MISSING_PATH) as f:
        missing = json.load(f)
    print(f'Missing: {len(missing):,}', flush=True)

    # Get all host names in CSV
    csv_hosts = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            for u in [row.get('url', ''), row.get('live_stream_url', '')]:
                m = re.match(r'https?://([^/]+)', u or '')
                if m:
                    h = m.group(1).lower()
                    if h.startswith('www.'):
                        h = h[4:]
                    csv_hosts.add(h)
    print(f'CSV hosts: {len(csv_hosts):,}', flush=True)

    # Categorize missing cams
    by_url_status = {'host_in_csv': 0, 'host_not_in_csv': 0, 'no_url': 0}
    examples = {'host_in_csv': [], 'host_not_in_csv': []}

    for c in missing:
        vu = c.get('videoUrl', '')
        iu = c.get('imageUrl', '')
        pu = c.get('playerUrl', '')
        su = c.get('sourceUrl', '')
        ipc = c.get('ipcamliveAlias', '')
        yt = c.get('youtubeVideoId', '')

        any_url = vu or iu or pu or su or ipc or yt
        if not any_url:
            by_url_status['no_url'] += 1
            continue

        # Check if any URL host is in CSV
        found = False
        for u in [vu, iu, pu, su, ipc]:
            if u:
                m = re.match(r'https?://([^/]+)', u)
                if m:
                    h = m.group(1).lower()
                    if h.startswith('www.'):
                        h = h[4:]
                    if h in csv_hosts:
                        found = True
                        break

        if found:
            by_url_status['host_in_csv'] += 1
            if len(examples['host_in_csv']) < 10:
                examples['host_in_csv'].append(c)
        else:
            by_url_status['host_not_in_csv'] += 1
            if len(examples['host_not_in_csv']) < 20:
                examples['host_not_in_csv'].append(c)

    print(f'\nCategorization:', flush=True)
    for k, v in by_url_status.items():
        print(f'  {k}: {v}', flush=True)

    print(f'\nExamples host_in_csv:', flush=True)
    for c in examples['host_in_csv'][:10]:
        print(f'  {c.get("source")}::{c.get("id")}', flush=True)
        for k in ['videoUrl', 'imageUrl', 'sourceUrl']:
            u = c.get(k, '')
            if u:
                print(f'    {k}: {u[:80]}', flush=True)

    print(f'\nExamples host_not_in_csv (NEW sources we should add):', flush=True)
    for c in examples['host_not_in_csv'][:20]:
        print(f'  {c.get("source")}::{c.get("id")}', flush=True)
        for k in ['videoUrl', 'imageUrl', 'sourceUrl']:
            u = c.get(k, '')
            if u:
                print(f'    {k}: {u[:80]}', flush=True)


if __name__ == '__main__':
    main()
