import urllib.request, json

# RIPE search for SACBO airport network
ips_to_try = ['2.112.0.1', '85.18.250.1', '85.35.231.1', '79.7.250.1']
for ip in ips_to_try:
    try:
        url = f'https://internetdb.shodan.io/{ip}'
        req = urllib.request.Request(url, headers={'User-Agent': 'eli6/1.0'})
        data = json.loads(urllib.request.urlopen(req, timeout=6).read())
        ports = data.get('ports', [])
        hosts = data.get('hostnames', [])
        print(f'{ip}: ports={ports[:5]}, hosts={hosts[:1]}')
    except Exception as e:
        print(f'{ip}: err')
