import urllib.request, json

# Try IPs near Orio al Serio airport via Shodan InternetDB (no API key needed)
# Orio al Serio airport coords: 45.6700, 9.7100
# Italian ranges often include TIM, Fastweb
ips_to_try = [
    '195.110.108.1', '2.34.0.1', '85.18.200.1', '85.35.226.1', '151.46.0.1',
    '85.18.50.1', '85.18.100.1', '85.35.50.1', '151.46.50.1', '151.46.100.1',
    '151.46.150.1', '85.35.100.1', '85.35.150.1', '85.35.200.1',
    '2.34.50.1', '2.34.100.1', '2.34.150.1', '2.34.200.1',
    '2.36.0.1', '2.36.50.1', '2.36.100.1',
    '79.7.50.1', '79.30.50.1', '79.30.100.1',
    '85.18.150.1', '85.18.200.1',
    '93.147.50.1', '93.147.100.1',
]
print('Scanning IPs near Orio al Serio:')
for ip in ips_to_try:
    try:
        url = f'https://internetdb.shodan.io/{ip}'
        req = urllib.request.Request(url, headers={'User-Agent': 'eli6/1.0'})
        data = json.loads(urllib.request.urlopen(req, timeout=6).read())
        ports = data.get('ports', [])
        hostnames = data.get('hostnames', [])
        asn = data.get('asn', '')
        city = data.get('city', '')
        country = data.get('country', '')
        if ports:
            print(f'  {ip}: {country}/{city} | asn={asn} | ports={ports[:5]} | hosts={hostnames[:2]}')
    except Exception as e:
        pass
