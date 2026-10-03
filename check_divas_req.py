"""Check working divas request."""
import json

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_video_url_flow.json') as f:
    data = json.load(f)
for d in data:
    if 'divas.cloud/VDS-API' in d.get('url', ''):
        print('URL:', d['url'])
        print('Method:', d.get('method', '?'))
        # Find post body
        for k, v in d.get('request_headers', {}).items():
            if k.lower() not in [':authority', ':method', ':path', ':scheme', 'accept-encoding', 'accept-language', 'sec-ch-ua', 'sec-ch-ua-mobile', 'sec-ch-ua-platform', 'sec-fetch-mode', 'sec-fetch-site', 'sec-fetch-dest', 'priority', 'user-agent', 'accept', 'origin', 'referer']:
                print(f'  Header: {k}: {v[:200]}')
        # Get body from request
        if d.get('request_post_data'):
            print(f'  Post body: {d["request_post_data"]}')
        break
