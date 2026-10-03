"""Get request body."""
import json
with open('fl511_video_url_flow.json') as f:
    data = json.load(f)
for d in data:
    if 'divas.cloud/VDS-API' in d.get('url', ''):
        body = d.get('request_post_data')
        if body:
            print(f'Request Body: {body}')
        print(f'Response: {d.get("body")}')
        break
