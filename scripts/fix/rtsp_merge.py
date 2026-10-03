"""Update rtsp_proxy_streams.json with all working streams."""
import json
import os


def main():
    # Load existing
    if os.path.exists('rtsp_proxy_streams.json'):
        with open('rtsp_proxy_streams.json') as f:
            existing = json.load(f)
    else:
        existing = {}
    print(f'Existing: {len(existing)} streams')

    # Load v2 results
    with open('rtsp_full_results_v2.json') as f:
        v2 = json.load(f)
    print(f'V2 results: {len(v2)} streams')

    # Build new
    new = {}
    for ip, path, creds, body in v2:
        # Build proxy key
        sid = f'{ip}_554_{path.replace("/", "_")}'
        if creds:
            url = f'rtsp://{creds}@{ip}:554{path}'
        else:
            url = f'rtsp://{ip}:554{path}'
        new[sid] = {
            'url': url,
            'ip': ip,
            'port': 554,
            'path': path,
            'creds': creds,
        }

    # Merge - prefer new results
    merged = {**existing, **new}
    print(f'Merged: {len(merged)}')

    # Save
    with open('rtsp_proxy_streams.json', 'w') as f:
        json.dump(merged, f, indent=2)
    print(f'Saved {len(merged)} streams to rtsp_proxy_streams.json')


if __name__ == '__main__':
    main()
