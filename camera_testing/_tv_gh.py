import urllib.request, socket, json
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://api.github.com/users/noah-eisenbruch/repos', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=10)
repos = json.loads(r.read())
for repo in repos:
    name = repo['name']
    desc = (repo.get('description') or '')[:80]
    print(f'{name}: {desc}')
    print(f"  https://github.com/noah-eisenbruch/{name}")
