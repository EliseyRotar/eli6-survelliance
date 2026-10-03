import urllib.request, socket, json
socket.setdefaulttimeout(15)
queries = ['traffic camera', 'live webcam', 'webcam directory', 'traffic webcam', 'cctv camera', 'public camera']
for q in queries:
    url = f'https://huggingface.co/api/datasets?search={q.replace(" ", "+")}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    r = urllib.request.urlopen(req, timeout=10)
    data = json.loads(r.read())
    print(f'\n{q}: {len(data)} datasets')
    for d in data[:5]:
        print(f"  {d.get('id', '')}: {(d.get('downloads') or 0)} dl")
