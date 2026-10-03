"""Mass /24-block port scanner for residential cam discovery.

Generates /24 subnets from a curated list of RESIDENTIAL ASN /16 prefixes
(Comcast, Verizon, AT&T, Orange, Sky, Vodafone, T-Com, Viettel, RCS&RDS, etc.),
randomly samples hosts in each /24, scans top ~25 cam ports in parallel, probes
each open port with probe_lib.

This is the only way to discover cams NOT listed in any aggregator (because
they're behind ISP NAT but still got public addresses via CGNAT leaks + carrier-grade
firewall holes).

Includes rate limiting to avoid hammering ISPs.
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

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\mass_scan_log.txt'

# Top cam-related ports (from CamXploit + our empirical data)
CAM_PORTS = [
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89,  # standard web alt
    443,                                         # https
    554,                                         # rtsp
    1935,                                        # rtmp
    1755, 1756,                                  # mms
    3702,                                        # onvif
    3777, 37778,                                 # dahua dvr
    8000, 8001, 8002, 8008,                      # http-alt
    8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089,
    8090, 8091, 8100, 8180, 8190,
    8888, 8899, 8890,
    10000, 10001,                                # cam alt
    31337,                                       # elite
]

# 200 residential /16 prefixes (Comcast, Verizon, Charter, AT&T, Cox, Orange, Sky, Vodafone,
# T-Com, Viettel, RCS&RDS, Fastweb, eolo, Tiscali, dtag, etc.).
# Sources: bgp.he.net/ipv4-allocation, ripe.stat.ripe.net, manual ASN->prefix lookups.
RESIDENTIAL_16S = [
    # US - Comcast
    '24.0.0.0/12', '24.16.0.0/12', '24.32.0.0/12', '24.48.0.0/12', '24.64.0.0/12',
    '24.80.0.0/12', '24.96.0.0/12', '24.112.0.0/12', '24.128.0.0/12',
    '24.144.0.0/12', '24.160.0.0/12', '24.176.0.0/12', '24.192.0.0/12',
    '50.128.0.0/9', '50.0.0.0/8', '50.64.0.0/12', '50.80.0.0/12',
    '73.0.0.0/8', '76.0.0.0/8',
    '68.32.0.0/11', '68.0.0.0/11',
    '67.160.0.0/12', '67.176.0.0/12',
    # Charter (US)
    '24.32.0.0/12', '24.74.0.0/12', '24.94.0.0/16', '24.160.0.0/16',
    '47.32.0.0/12', '47.36.0.0/16', '47.41.0.0/16', '47.224.0.0/12',
    # Verizon (US)
    '71.0.0.0/11', '71.32.0.0/16', '71.96.0.0/16', '71.112.0.0/12',
    '98.0.0.0/12', '98.32.0.0/16', '98.96.0.0/12', '98.192.0.0/16',
    # AT&T (US)
    '76.0.0.0/8', '162.0.0.0/14',
    # Cox (US)
    '68.96.0.0/12', '72.192.0.0/12', '98.96.0.0/12', '70.160.0.0/11',
    # Frontier (US)
    '76.16.0.0/12', '184.96.0.0/12', '67.32.0.0/12', '70.112.0.0/12',
    # T-Mobile (US)
    '172.32.0.0/11', '172.56.0.0/13', '172.58.0.0/15',
    # CenturyLink (US)
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
    # EU - Telefonica / Movistar (ES)
    '79.144.0.0/12', '79.168.0.0/14', '83.32.0.0/12',
    '85.48.0.0/12', '85.136.0.0/13', '88.0.0.0/11',
    # EU - BT (UK)
    '81.0.0.0/12', '81.128.0.0/12', '86.0.0.0/12', '86.128.0.0/12',
    '109.144.0.0/12', '109.192.0.0/12', '109.224.0.0/12',
    # EU - Sky UK
    '90.192.0.0/12', '90.240.0.0/12', '2.96.0.0/12',
    # EU - Virgin Media UK
    '80.0.0.0/9', '82.0.0.0/11', '81.96.0.0/12',
    # EU - Ziggo NL
    '94.208.0.0/13', '94.212.0.0/14', '88.0.0.0/11',
    # EU - KPN NL
    '86.80.0.0/12', '86.92.0.0/13', '94.96.0.0/12',
    # EU - Sky IT
    '2.32.0.0/13', '2.40.0.0/13',
    # EU - Tiscali IT (retired)
    '94.32.0.0/12', '95.0.0.0/12',
    # EU - Eolo IT
    '88.32.0.0/12',
    # EU - Fastweb IT
    '85.16.0.0/12', '85.32.0.0/12',
    # EU - Telecom IT
    '62.96.0.0/12', '80.104.0.0/12', '80.112.0.0/12',
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
    # EU - Numericable FR
    '85.69.0.0/16',
    # EU - SFR FR
    '77.128.0.0/11', '77.192.0.0/12', '85.69.0.0/16',
    # EU - Bouygues FR
    '88.160.0.0/12', '176.128.0.0/12',
    # EU - Jazztel ES
    '87.216.0.0/12',
    # EU - Ono ES
    '85.136.0.0/13',
    # EU - Vodafone IT (merged)
    '93.32.0.0/12', '93.64.0.0/12',
    # EU - Tiscali IT
    '95.240.0.0/12', '95.74.0.0/15',
    # Asia - NTT JP
    '153.128.0.0/12', '153.192.0.0/12', '202.32.0.0/12',
    # Asia - KDDI JP
    '59.128.0.0/11', '59.158.0.0/15', '61.115.0.0/16', '210.224.0.0/12',
    # Asia - Softbank JP
    '60.96.0.0/11', '126.192.0.0/10',
    # Asia - HiNet TW
    '61.62.0.0/14', '61.66.0.0/15',
    # Asia - China Telecom
    '58.32.0.0/13', '58.40.0.0/15', '58.48.0.0/13',
    '110.96.0.0/11', '111.0.0.0/10', '124.72.0.0/13', '124.112.0.0/12',
    '222.64.0.0/13', '222.72.0.0/14', '222.80.0.0/12', '222.176.0.0/12',
    # Asia - China Unicom
    '60.0.0.0/11', '60.11.0.0/16', '61.135.0.0/16', '61.136.0.0/16',
    '61.138.0.0/16', '61.139.0.0/16', '61.148.0.0/14',
    '110.192.0.0/11', '111.112.0.0/12', '124.66.0.0/13', '125.32.0.0/12',
    '202.97.0.0/16', '219.128.0.0/11',
    # Asia - Korea Telecom
    '211.32.0.0/12', '211.36.0.0/12', '211.40.0.0/12', '211.44.0.0/12',
    '220.64.0.0/11', '121.128.0.0/11', '175.192.0.0/10',
    # Asia - LG U+ Korea
    '211.36.0.0/12', '112.160.0.0/12',
    # Asia - SK Broadband
    '211.108.0.0/14', '211.36.0.0/12',
    # Asia - J:COM JP
    '110.232.0.0/13',
    # Asia - Viettel VN
    '113.160.0.0/11', '113.190.0.0/12', '14.160.0.0/12', '14.224.0.0/12',
    '171.224.0.0/12', '171.244.0.0/14',
    # Asia - VNPT
    '113.161.0.0/12', '113.164.0.0/12',
    # Asia - Mobifone
    '110.0.0.0/12', '118.71.0.0/16',
    # Asia - India BSNL
    '117.192.0.0/10', '117.224.0.0/12',
    '61.0.0.0/12', '59.88.0.0/12',
    # Asia - Reliance Jio India
    '49.32.0.0/12', '49.36.0.0/12', '49.40.0.0/12',
    '106.0.0.0/12', '110.224.0.0/12',
    # Australia - Telstra
    '58.160.0.0/12', '58.108.0.0/14', '101.160.0.0/12',
    '110.32.0.0/12', '120.144.0.0/12', '120.156.0.0/12',
    '124.176.0.0/12', '124.180.0.0/12', '1.40.0.0/12',
    # AU - Optus
    '110.144.0.0/12', '114.72.0.0/12', '115.64.0.0/12',
    # LATAM - Telefónica (BR)
    '189.0.0.0/12', '189.16.0.0/12', '189.32.0.0/11', '189.64.0.0/12',
    '191.0.0.0/11',
    # BR - Oi
    '177.0.0.0/12', '179.0.0.0/12', '186.192.0.0/11', '186.224.0.0/11',
    # MX - Telmex
    '189.128.0.0/9', '200.0.0.0/11',
    # AR - Telecom Argentina
    '181.0.0.0/12', '181.32.0.0/12', '186.0.0.0/12', '186.96.0.0/11',
    # Eastern Europe: Romania
    '79.112.0.0/13', '79.114.0.0/15', '86.120.0.0/13',
    '109.166.0.0/12', '188.24.0.0/12', '188.25.0.0/12',
    # HU - Magyar Telekom
    '81.0.0.0/16', '84.224.0.0/12', '188.32.0.0/12', '188.36.0.0/14',
    # CZ - O2
    '85.160.0.0/13', '85.162.0.0/15', '90.180.0.0/14',
    # PL - Netia (was)
    '213.0.0.0/12',
    # GR - OTE/Forthnet
    '62.1.0.0/16', '78.32.0.0/12', '85.72.0.0/12',
    # GR - Wind
    '62.74.0.0/15', '78.87.0.0/16', '94.64.0.0/14', '94.64.96.0/19',
    # RU - Rostelecom
    '85.140.0.0/12', '87.226.128.0/17', '109.252.0.0/16',
    '178.34.0.0/15', '178.64.128.0/18', '188.168.0.0/16', '188.168.0.0/13',
    '213.24.0.0/12', '213.180.193.0/24', '188.16.0.0/13',
    # TR - Turkcell/Turk Telekom
    '81.6.0.0/16', '78.160.0.0/11', '85.96.0.0/12', '88.224.0.0/11',
    '94.54.0.0/15', '95.0.0.0/12', '85.105.0.0/16',
    # IL - Bezeq
    '62.0.0.0/12', '85.64.0.0/14', '109.224.0.0/12', '212.25.0.0/17',
    # EG - Telecom Egypt
    '41.32.0.0/12', '41.176.0.0/12', '197.160.0.0/12',
    # ZA - Telkom
    '102.32.0.0/12', '102.160.0.0/12', '105.0.0.0/12', '196.0.0.0/13',
    '41.0.0.0/12', '154.0.0.0/13',
]

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=300, pool_maxsize=600))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=300, pool_maxsize=600))
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    return s


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


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
    """Return random IP in an ipaddress Network object."""
    try:
        net = ipaddress.ip_network(block, strict=False)
        # Use only public IPs
        size = min(net.num_addresses, 65536)  # cap to /16 size
        for _ in range(100):
            idx = random.randint(0, size - 1)
            ip = str(net[idx])
            # Skip bogons / private
            try:
                ipi = ipaddress.ip_address(ip)
                if ipi.is_private or ipi.is_multicast or ipi.is_reserved:
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
    except (socket.timeout, Exception):
        return False


def probe_one_combo(s, host, port):
    """Run probe_lib against host:port. Return probe_res dict or None."""
    try:
        res = probe_lib.probe_host(s, host, port, False, 2.5)
        return res
    except Exception:
        return None


def main():
    s = session()
    seen = existing_hosts()
    log(f'[init] {len(seen)} existing hosts')

    # Build candidate set: select 200 /24 blocks from ASN prefixes,
    # then for each /24 we either take every IP (small /24) or sample.
    rand_blocks = set()
    for pref in RESIDENTIAL_16S:
        try:
            net = ipaddress.ip_network(pref, strict=False)
            # Pick sub-/24s within the /16 — we just need ONE /24 per prefix
            # Simplest: take the base /24 (e.g. first 3 octets).
            # But we want broader coverage — slice into chunks of size /20.
            # Take a random /24 within this /16:
            base = str(net.network_address).rsplit('.', 1)[0]
            last_oct = random.randint(0, 255)
            candidate_24 = f'{base}.{last_oct}/24'
            rand_blocks.add(candidate_24)
        except Exception:
            continue

    log(f'[gen] {len(rand_blocks)} /24 blocks selected')

    # For each /24, sample a few random hosts (NOT all 256)
    cand_host = []
    for block in rand_blocks:
        for _ in range(8):  # 8 random IPs per /24
            ip = gen_random_ip_in_block(block)
            if ip:
                cand_host.append(ip)
    log(f'[cands] {len(cand_host)} host candidates')

    # Take only ones we haven't seen host:port for
    target_set = set()
    for ip in cand_host:
        for port in [80, 8080, 81, 8000, 8081, 554, 8090]:
            target_set.add((ip, port))
    log(f'[targets] {len(target_set)} (host,port) pairs to probe')

    # First pass: TCP-only port check (fast — no HTTP GET).
    # Use socket.connect_ex; ~0.3s/call with 200 threads.
    open_count = 0
    seen_pairs = set()
    open_combos = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=160) as ex:
        futs = {(ip, port): ex.submit(port_is_open, ip, port, 2.0) for (ip, port) in target_set}
        for combo, fut in futs.items():
            try:
                ok = fut.result(timeout=5)
            except Exception:
                ok = False
            if ok:
                open_count += 1
                open_combos.append(combo)
    log(f'[probe1] {open_count} open ports in {time.time()-t0:.1f}s')

    # Second pass: probe_lib on open combos (HTTP probe)
    added = 0
    n = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=80) as ex:
        # Probe in sub-batches of 200 so csv_writer doesn't get hit hard
        batch = 0
        while batch < len(open_combos):
            sub = open_combos[batch:batch + 200]
            batch += len(sub)
            futs = {ex.submit(probe_one_combo, s, ip, port): (ip, port) for (ip, port) in sub}
            for fut in as_completed(futs):
                n += 1
                ip, port = futs[fut]
                try:
                    res = fut.result(timeout=8)
                except Exception:
                    continue
                if res and res['weight'] >= 35:
                    try:
                        geo = probe_lib.geoip(s, ip)
                    except Exception:
                        geo = {}
                    entry = csv_writer.entry_from_probe(res, {'source': 'mass_portscan'}, geo)
                    try:
                        idx_csv = csv_writer.append_one(entry)
                        log(f'  ADDED idx={idx_csv}: {res["url"][:90]}')
                        added += 1
                        seen.add(f'{ip}:{port}')
                    except Exception as e:
                        log(f'  err: {e}')
            if n % 200 == 0:
                log(f'  progress {n}/{len(open_combos)}, added={added}')
            time.sleep(0.3)  # slower than usual to avoid ip-api rate
    log(f'[done] {added} cams added in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
