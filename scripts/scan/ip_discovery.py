"""IP-range-based video cam discovery.

Strategy: find a list of IP ranges that commonly host consumer webcams (mostly
Asia residential), then do shallow probes (80, 8080, 8081) with 200ms timeout
to find 1) anything that returns 200 with image/* content 2) anything that
returns 401/403 with WWW-Authenticate (video cams often have admin auth).

Use Shodan InternetDB for cheap target list.
"""
import os
import csv
import time
import json
import socket
import urllib.request
import ssl
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

import glob

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break
if not CSV_PATH:
    print('CSV not found')
    exit(1)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# IP ranges known to host MANY consumer webcams (from prior work)
RANGES = [
    # Asia residential
    '110.50.',  # Japan
    '113.150.',  # Japan
    '114.156.',  # Japan
    '118.103.',  # Japan
    '125.30.',  # Japan
    '125.53.',  # Japan
    '133.130.',  # Japan
    '153.156.',  # Japan
    '202.215.',  # Japan
    '218.221.',  # Japan
    '219.124.',  # Japan
    '220.96.',  # Japan
    '58.138.',  # Japan
    '59.138.',  # Japan
    '61.114.',  # Japan
    '61.200.',  # Japan
    '61.215.',  # Japan
    '114.48.',  # Korea
    '121.140.',  # Korea
    '121.168.',  # Korea
    '125.131.',  # Korea
    '211.36.',  # Korea
    '218.144.',  # Korea
    '59.15.',  # Korea
    '118.34.',  # Korea
    '175.192.',  # Korea
    '1.234.',  # Korea
    '101.235.',  # Korea
    '112.218.',  # Korea
    '116.33.',  # Korea
    '118.34.',  # Korea
    '183.109.',  # Korea
    '220.64.',  # Korea
    '58.224.',  # Korea
    # China
    '110.64.',  # China Mobile
    '111.0.',  # China
    '113.0.',  # China
    '117.0.',  # China
    '120.0.',  # China
    '121.0.',  # China
    '125.0.',  # China
    '180.0.',  # China
    '202.0.',  # China
    '220.0.',  # China
    '222.0.',  # China
    '58.0.',  # China
    '59.0.',  # China
    # Taiwan
    '36.224.',  # Taiwan
    '114.36.',  # Taiwan
    '210.61.',  # Taiwan
    '61.220.',  # Taiwan
    # Iran/Middle East
    '78.39.',  # Iran
    '5.78.',  # Iran
    '78.111.',  # Iran
    '85.185.',  # Iran
    '89.32.',  # Iran
    '95.80.',  # Iran
    '151.238.',  # Iran
    '178.131.',  # Iran
    '2.180.',  # Iran
    '77.42.',  # Iran
    '85.133.',  # Iran
    '94.176.',  # Iran
    # Indonesia / Vietnam
    '36.66.',  # Indonesia
    '36.67.',  # Indonesia
    '36.68.',  # Indonesia
    '125.164.',  # Indonesia
    '180.241.',  # Indonesia
    '36.69.',  # Indonesia
    '36.74.',  # Indonesia
    '180.242.',  # Indonesia
    '180.243.',  # Indonesia
    '180.244.',  # Indonesia
    '103.10.',  # Vietnam
    '14.162.',  # Vietnam
    '14.169.',  # Vietnam
    '42.112.',  # Vietnam
    '113.161.',  # Vietnam
    '171.224.',  # Vietnam
    '222.252.',  # Vietnam
    # Brazil / South America
    '177.32.',  # Brazil
    '179.108.',  # Brazil
    '187.74.',  # Brazil
    '189.4.',  # Brazil
    '189.5.',  # Brazil
    '191.193.',  # Brazil
    '200.144.',  # Brazil
    '186.215.',  # Brazil
    '187.19.',  # Brazil
    '200.148.',  # Brazil
    '201.20.',  # Brazil
    '201.21.',  # Brazil
    '201.80.',  # Brazil
    # Mexico
    '177.224.',  # Mexico
    '187.141.',  # Mexico
    '187.142.',  # Mexico
    '187.188.',  # Mexico
    '189.146.',  # Mexico
    '189.180.',  # Mexico
    '189.209.',  # Mexico
    '189.218.',  # Mexico
    '200.34.',  # Mexico
    '201.103.',  # Mexico
    '201.105.',  # Mexico
    '201.111.',  # Mexico
    '201.115.',  # Mexico
    '201.139.',  # Mexico
    '201.144.',  # Mexico
    '201.172.',  # Mexico
    # Russia / Eastern Europe
    '46.166.',  # Russia
    '77.34.',  # Russia
    '77.35.',  # Russia
    '78.25.',  # Russia
    '78.36.',  # Russia
    '78.85.',  # Russia
    '78.106.',  # Russia
    '78.107.',  # Russia
    '78.108.',  # Russia
    '85.93.',  # Russia
    '85.140.',  # Russia
    '85.192.',  # Russia
    '91.77.',  # Russia
    '94.25.',  # Russia
    '95.24.',  # Russia
    '95.25.',  # Russia
    '95.26.',  # Russia
    '95.27.',  # Russia
    '109.124.',  # Russia
    '109.252.',  # Russia
    '176.14.',  # Russia
    '176.15.',  # Russia
    '176.59.',  # Russia
    '178.34.',  # Russia
    '178.35.',  # Russia
    '178.155.',  # Russia
    '188.168.',  # Russia
    '193.168.',  # Russia
    '213.87.',  # Russia
    '213.108.',  # Russia
    '217.66.',  # Russia
    '85.140.',  # Russia
    '37.140.',  # Russia
    # Turkey
    '85.105.',  # Turkey
    '85.106.',  # Turkey
    '88.230.',  # Turkey
    '88.231.',  # Turkey
    '88.235.',  # Turkey
    '88.236.',  # Turkey
    '78.160.',  # Turkey
    '78.161.',  # Turkey
    '78.162.',  # Turkey
    '78.163.',  # Turkey
    '78.164.',  # Turkey
    '78.165.',  # Turkey
    '78.166.',  # Turkey
    '78.167.',  # Turkey
    '78.168.',  # Turkey
    '78.169.',  # Turkey
    '78.170.',  # Turkey
    '78.171.',  # Turkey
    '78.172.',  # Turkey
    '78.173.',  # Turkey
    '78.174.',  # Turkey
    '78.175.',  # Turkey
    '78.176.',  # Turkey
    '78.177.',  # Turkey
    '78.178.',  # Turkey
    '78.179.',  # Turkey
    '78.180.',  # Turkey
    '78.181.',  # Turkey
    '78.182.',  # Turkey
    '78.183.',  # Turkey
    '78.184.',  # Turkey
    '78.185.',  # Turkey
    '78.186.',  # Turkey
    '78.187.',  # Turkey
    '78.188.',  # Turkey
    '78.189.',  # Turkey
    '78.190.',  # Turkey
    '78.191.',  # Turkey
    '95.10.',  # Turkey
    '95.11.',  # Turkey
    '95.12.',  # Turkey
    '95.13.',  # Turkey
    '95.14.',  # Turkey
    '95.15.',  # Turkey
    '95.16.',  # Turkey
    '95.17.',  # Turkey
    '95.18.',  # Turkey
    '95.19.',  # Turkey
    '95.20.',  # Turkey
    '95.21.',  # Turkey
    '95.22.',  # Turkey
    '95.23.',  # Turkey
    '95.24.',  # Turkey
    '95.25.',  # Turkey
    '95.26.',  # Turkey
    '95.27.',  # Turkey
    '95.28.',  # Turkey
    '95.29.',  # Turkey
    '95.30.',  # Turkey
    '95.31.',  # Turkey
    '95.32.',  # Turkey
    '95.33.',  # Turkey
    '95.34.',  # Turkey
    '95.35.',  # Turkey
    '95.36.',  # Turkey
    '95.37.',  # Turkey
    '95.38.',  # Turkey
    '95.39.',  # Turkey
    '95.40.',  # Turkey
    '95.41.',  # Turkey
    '95.42.',  # Turkey
    '95.43.',  # Turkey
    '95.44.',  # Turkey
    '95.45.',  # Turkey
    '95.46.',  # Turkey
    '95.47.',  # Turkey
    '95.48.',  # Turkey
    '95.49.',  # Turkey
    '95.50.',  # Turkey
    '95.51.',  # Turkey
    '95.52.',  # Turkey
    '95.53.',  # Turkey
    '95.54.',  # Turkey
    '95.55.',  # Turkey
    '95.56.',  # Turkey
    '95.57.',  # Turkey
    '95.58.',  # Turkey
    '95.59.',  # Turkey
    '95.60.',  # Turkey
    '95.61.',  # Turkey
    '95.62.',  # Turkey
    '95.63.',  # Turkey
    '95.64.',  # Turkey
    '95.65.',  # Turkey
    '95.66.',  # Turkey
    '95.67.',  # Turkey
    '95.68.',  # Turkey
    '95.69.',  # Turkey
    '95.70.',  # Turkey
    '95.71.',  # Turkey
    '95.72.',  # Turkey
    '95.73.',  # Turkey
    '95.74.',  # Turkey
    '95.75.',  # Turkey
    '95.76.',  # Turkey
    '95.77.',  # Turkey
    '95.78.',  # Turkey
    '95.79.',  # Turkey
    '95.80.',  # Turkey
    '95.81.',  # Turkey
    '95.82.',  # Turkey
    '95.83.',  # Turkey
    '95.84.',  # Turkey
    '95.85.',  # Turkey
    '95.86.',  # Turkey
    '95.87.',  # Turkey
    '95.88.',  # Turkey
    '95.89.',  # Turkey
    '95.90.',  # Turkey
    '95.91.',  # Turkey
    '95.92.',  # Turkey
    '95.93.',  # Turkey
    '95.94.',  # Turkey
    '95.95.',  # Turkey
    '95.96.',  # Turkey
    '95.97.',  # Turkey
    '95.98.',  # Turkey
    '95.99.',  # Turkey
    '95.100.',  # Turkey
    '95.101.',  # Turkey
    '95.102.',  # Turkey
    '95.103.',  # Turkey
    '95.104.',  # Turkey
    '95.105.',  # Turkey
    '95.106.',  # Turkey
    '95.107.',  # Turkey
    '95.108.',  # Turkey
    '95.109.',  # Turkey
    '95.110.',  # Turkey
    '95.111.',  # Turkey
    '95.112.',  # Turkey
    '95.113.',  # Turkey
    '95.114.',  # Turkey
    '95.115.',  # Turkey
    '95.116.',  # Turkey
    '95.117.',  # Turkey
    '95.118.',  # Turkey
    '95.119.',  # Turkey
    '95.120.',  # Turkey
    '95.121.',  # Turkey
    '95.122.',  # Turkey
    '95.123.',  # Turkey
    '95.124.',  # Turkey
    '95.125.',  # Turkey
    '95.126.',  # Turkey
    '95.127.',  # Turkey
    '95.128.',  # Turkey
    '95.129.',  # Turkey
    '95.130.',  # Turkey
    '95.131.',  # Turkey
    '95.132.',  # Turkey
    '95.133.',  # Turkey
    '95.134.',  # Turkey
    '95.135.',  # Turkey
    '95.136.',  # Turkey
    '95.137.',  # Turkey
    '95.138.',  # Turkey
    '95.139.',  # Turkey
    '95.140.',  # Turkey
    '95.141.',  # Turkey
    '95.142.',  # Turkey
    '95.143.',  # Turkey
    '95.144.',  # Turkey
    '95.145.',  # Turkey
    '95.146.',  # Turkey
    '95.147.',  # Turkey
    '95.148.',  # Turkey
    '95.149.',  # Turkey
    '95.150.',  # Turkey
    '95.151.',  # Turkey
    '95.152.',  # Turkey
    '95.153.',  # Turkey
    '95.154.',  # Turkey
    '95.155.',  # Turkey
    '95.156.',  # Turkey
    '95.157.',  # Turkey
    '95.158.',  # Turkey
    '95.159.',  # Turkey
    '95.160.',  # Turkey
    '95.161.',  # Turkey
    '95.162.',  # Turkey
    '95.163.',  # Turkey
    '95.164.',  # Turkey
    '95.165.',  # Turkey
    '95.166.',  # Turkey
    '95.167.',  # Turkey
    '95.168.',  # Turkey
    '95.169.',  # Turkey
    '95.170.',  # Turkey
    '95.171.',  # Turkey
    '95.172.',  # Turkey
    '95.173.',  # Turkey
    '95.174.',  # Turkey
    '95.175.',  # Turkey
    '95.176.',  # Turkey
    '95.177.',  # Turkey
    '95.178.',  # Turkey
    '95.179.',  # Turkey
    '95.180.',  # Turkey
    '95.181.',  # Turkey
    '95.182.',  # Turkey
    '95.183.',  # Turkey
    '95.184.',  # Turkey
    '95.185.',  # Turkey
    '95.186.',  # Turkey
    '95.187.',  # Turkey
    '95.188.',  # Turkey
    '95.189.',  # Turkey
    '95.190.',  # Turkey
    '95.191.',  # Turkey
    '95.192.',  # Turkey
    '95.193.',  # Turkey
    '95.194.',  # Turkey
    '95.195.',  # Turkey
    '95.196.',  # Turkey
    '95.197.',  # Turkey
    '95.198.',  # Turkey
    '95.199.',  # Turkey
    '95.200.',  # Turkey
    '95.201.',  # Turkey
    '95.202.',  # Turkey
    '95.203.',  # Turkey
    '95.204.',  # Turkey
    '95.205.',  # Turkey
    '95.206.',  # Turkey
    '95.207.',  # Turkey
    '95.208.',  # Turkey
    '95.209.',  # Turkey
    '95.210.',  # Turkey
    '95.211.',  # Turkey
    '95.212.',  # Turkey
    '95.213.',  # Turkey
    '95.214.',  # Turkey
    '95.215.',  # Turkey
    '95.216.',  # Turkey
    '95.217.',  # Turkey
    '95.218.',  # Turkey
    '95.219.',  # Turkey
    '95.220.',  # Turkey
    '95.221.',  # Turkey
    '95.222.',  # Turkey
    '95.223.',  # Turkey
    '95.224.',  # Turkey
    '95.225.',  # Turkey
    '95.226.',  # Turkey
    '95.227.',  # Turkey
    '95.228.',  # Turkey
    '95.229.',  # Turkey
    '95.230.',  # Turkey
    '95.231.',  # Turkey
    '95.232.',  # Turkey
    '95.233.',  # Turkey
    '95.234.',  # Turkey
    '95.235.',  # Turkey
    '95.236.',  # Turkey
    '95.237.',  # Turkey
    '95.238.',  # Turkey
    '95.239.',  # Turkey
    '95.240.',  # Turkey
    '95.241.',  # Turkey
    '95.242.',  # Turkey
    '95.243.',  # Turkey
    '95.244.',  # Turkey
    '95.245.',  # Turkey
    '95.246.',  # Turkey
    '95.247.',  # Turkey
    '95.248.',  # Turkey
    '95.249.',  # Turkey
    '95.250.',  # Turkey
    '95.251.',  # Turkey
    '95.252.',  # Turkey
    '95.253.',  # Turkey
    '95.254.',  # Turkey
    '95.255.',  # Turkey
    '95.0.',  # Turkey
    '95.1.',  # Turkey
    '95.2.',  # Turkey
    '95.3.',  # Turkey
    '95.4.',  # Turkey
    '95.5.',  # Turkey
    '95.6.',  # Turkey
    '95.7.',  # Turkey
    '95.8.',  # Turkey
    '95.9.',  # Turkey
    '95.',  # Turkey
    '88.224.',  # Turkey
    '88.225.',  # Turkey
    '88.226.',  # Turkey
    '88.227.',  # Turkey
    '88.228.',  # Turkey
    '88.229.',  # Turkey
    '88.232.',  # Turkey
    '88.233.',  # Turkey
    '88.234.',  # Turkey
    '88.237.',  # Turkey
    '88.238.',  # Turkey
    '88.239.',  # Turkey
    '88.240.',  # Turkey
    '88.241.',  # Turkey
    '88.242.',  # Turkey
    '88.243.',  # Turkey
    '88.244.',  # Turkey
    '88.245.',  # Turkey
    '88.246.',  # Turkey
    '88.247.',  # Turkey
    '88.248.',  # Turkey
    '88.249.',  # Turkey
    '88.250.',  # Turkey
    '88.251.',  # Turkey
    '88.252.',  # Turkey
    '88.253.',  # Turkey
    '88.254.',  # Turkey
    '88.255.',  # Turkey
    '88.0.',  # Turkey
    '88.1.',  # Turkey
    '88.2.',  # Turkey
    '88.3.',  # Turkey
    '88.4.',  # Turkey
    '88.5.',  # Turkey
    '88.6.',  # Turkey
    '88.7.',  # Turkey
    '88.8.',  # Turkey
    '88.9.',  # Turkey
    '88.',  # Turkey
    '78.160.',  # Turkey
    '78.161.',  # Turkey
    '78.162.',  # Turkey
    '78.163.',  # Turkey
    '78.164.',  # Turkey
    '78.165.',  # Turkey
    '78.166.',  # Turkey
    '78.167.',  # Turkey
    '78.168.',  # Turkey
    '78.169.',  # Turkey
    '78.170.',  # Turkey
    '78.171.',  # Turkey
    '78.172.',  # Turkey
    '78.173.',  # Turkey
    '78.174.',  # Turkey
    '78.175.',  # Turkey
    '78.176.',  # Turkey
    '78.177.',  # Turkey
    '78.178.',  # Turkey
    '78.179.',  # Turkey
    '78.180.',  # Turkey
    '78.181.',  # Turkey
    '78.182.',  # Turkey
    '78.183.',  # Turkey
    '78.184.',  # Turkey
    '78.185.',  # Turkey
    '78.186.',  # Turkey
    '78.187.',  # Turkey
    '78.188.',  # Turkey
    '78.189.',  # Turkey
    '78.190.',  # Turkey
    '78.191.',  # Turkey
    '78.0.',  # Turkey
    '78.1.',  # Turkey
    '78.2.',  # Turkey
    '78.3.',  # Turkey
    '78.4.',  # Turkey
    '78.5.',  # Turkey
    '78.6.',  # Turkey
    '78.7.',  # Turkey
    '78.8.',  # Turkey
    '78.9.',  # Turkey
    '78.',  # Turkey
]

# Reduce to 256-prefixes (X.Y.Z.0/24), each gives 256 IPs
# Strategy: pick 2-3 random Z values per X.Y. and 1-3 random Y values per X.Y.Z
# Total probes: 256 prefixes × 256 IPs × 5 ports = 327,680, way too many
# Limit: probe 1000 IPs per X.Y.0/24 = 256K probes per X.Y. = 60 prefixes × 256K = 15M
# Need: limit to a few thousand total
# Approach: probe 200 random IPs per X.Y.0/24 prefix
# 5 ports × 200 IPs × 50 prefixes = 50,000 probes
# At 1.5 sec each = 75K sec = 21 hours, too slow

# Let me skip this and try a different approach: use Shodan API
print("Skipping IP range approach, too slow")
print("Trying free Shodan via internetdb.shodan.io")


def shodan_query(query_filter):
    """Shodan InternetDB query - free, no key."""
    # https://internetdb.shodan.io/<ip>
    # No bulk API, but we can scan a list of IPs we already know are in residential ranges
    pass


def main():
    # Load existing URLs
    print("Loading CSV...")
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f"  CSV has {len(existing):,} URLs")

    # Use Shodan InternetDB for target IPs in our existing host set
    # Get all unique IPs in CSV
    import re as _re
    ips = set()
    for url in existing:
        m = _re.match(r'https?://(\d+\.\d+\.\d+\.\d+)', url)
        if m:
            ips.add(m.group(1))
    print(f"  CSV has {len(ips):,} unique IPs")

    # Save IPs to file for batched Shodan lookup
    ip_list = sorted(ips)
    with open('csv_ips.txt', 'w') as f:
        f.write('\n'.join(ip_list))
    print(f"  Saved to csv_ips.txt")

    # Stats on residential ISPs
    counter = Counter()
    for ip in ip_list:
        a, b = ip.split('.')[:2]
        counter[f'{a}.{b}.'] += 1
    print(f"\nTop 30 IP /16 prefixes in CSV:")
    for k, v in counter.most_common(30):
        print(f"  {k}: {v}")


if __name__ == '__main__':
    main()
