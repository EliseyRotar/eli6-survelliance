import urllib.request, socket, json
socket.setdefaulttimeout(8)
for s in ['caltrans', 'erau', 'windy', 'insecam', 'tfl', 'argus', 'ccitv', '511ny', 'wxyz', 'txdot', 'fdot', 'oktraffic', 'bpjt', 'nycdot', '511ga']:
    url = f'https://data.trafficvision.live/camera-data/{s}-cameras.json'
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=5)
        body = r.read().decode('utf-8', errors='replace')
        if 'DOCTYPE html' in body:
            print(f'{s}: 200 (HTML)')
            continue
        data = json.loads(body)
        meta = data.get('_metadata', {})
        print(f'{s}: 200 cameras={meta.get("cameraCount", "?")} v={meta.get("videoCameraCount", 0)} i={meta.get("imageCameraCount", 0)}')
    except Exception as e:
        print(f'{s}: {str(e)[:60]}')
