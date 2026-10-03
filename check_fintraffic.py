"""Try to find specific fintraffic cam URLs from the catalog IDs.

The TV catalog has IDs like 'fintraffic-c01503'. We try the
liikennetilanne.fintraffic.fi site to find the actual cam URL.
"""
import json
import re
import sys
import time
import urllib.request
import ssl

sys.stdout.reconfigure(line_buffering=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read(2*1024*1024).decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return -1, ''


def main():
    with open('tv_missing.json') as f:
        missing = json.load(f)
    # Filter to fintraffic
    fintraffic = [c for c in missing if c.get('source') == 'fintraffic']
    print(f'fintraffic missing: {len(fintraffic)}', flush=True)

    # Try the home page first
    status, html = fetch('https://liikennetilanne.fintraffic.fi/', timeout=10)
    print(f'Home page: {status}, {len(html)} bytes', flush=True)
    if status == 200:
        # Find any cam-related URLs
        for m in re.finditer(r'(https?://[^\s"\'<>]+\.jpg)', html, re.I):
            print(f'  jpg: {m.group(1)[:100]}', flush=True)
            break
        for m in re.finditer(r'(https?://[^\s"\'<>]+/camera[^\s"\'<>]*)', html, re.I):
            print(f'  camera: {m.group(1)[:100]}', flush=True)
        for m in re.finditer(r'(https?://[^\s"\'<>]+/webcam[^\s"\'<>]*)', html, re.I):
            print(f'  webcam: {m.group(1)[:100]}', flush=True)

    # Try fintraffic API
    for ep in [
        'https://liikennetilanne.fintraffic.fi/api/v1/webcams',
        'https://liikennetilanne.fintraffic.fi/api/webcams',
        'https://api.fintraffic.fi/webcams',
        'https://api.fintraffic.fi/v1/webcams',
        'https://api.fintraffic.fi/v2/webcams',
    ]:
        status, html = fetch(ep, timeout=10)
        print(f'\n{ep}: {status}, {len(html)} bytes', flush=True)
        if status == 200 and 'json' in html[:200].lower() or '"webcam' in html.lower() or '"camera' in html.lower():
            # Try parse as JSON
            try:
                d = json.loads(html)
                if isinstance(d, dict) and 'webcams' in d:
                    print(f'  found {len(d["webcams"])} webcams!', flush=True)
                    # Save
                    with open('fintraffic_api.json', 'w') as f:
                        json.dump(d, f, indent=2)
                    return
                elif isinstance(d, list):
                    print(f'  list with {len(d)} items', flush=True)
                    with open('fintraffic_api.json', 'w') as f:
                        json.dump(d, f, indent=2)
                    return
            except:
                pass
        time.sleep(0.5)


if __name__ == '__main__':
    main()
