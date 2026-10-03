|# Bruteforce Module

**Purpose**: Comprehensive cam brute-forcing, CVE exploitation, and authentication bypass toolkit.

## Layout

```
bruteforce/
├── README.md                          (this file)
├── framework/                         # Core BF modules
│   ├── advanced_bruteforce.py          # Multi-threaded generic BF
│   ├── bruteforce_test.py              # Standalone BF testing
│   ├── cam_mass_bruteforce.py          # Mass scan + BF combined
│   ├── iot_webcam_bruteforce.py        # IoT cam BF (basic)
│   ├── iot_webcam_bruteforce_ultimate.py  # IoT cam BF (full)
│   ├── launcher.py                     # GUI launcher
│   ├── mass_bf_all.py                  # Parallel BF across all cams
│   ├── smart_bruteforce.py             # Smart BF (brand detection)
│   ├── ultimate_bruteforce.py          # 1000+ creds × 25+ brands
│   ├── camera_bruteforce.py            # Original scanner
│   └── apply_bf_results.py             # Apply BF results to CSV
│
├── vendor_specific/                   # Vendor-specific exploits
│   ├── hikvision/                      # Hikvision tools
│   │   ├── cve_2017_7921.py           # CVE-2017-7921 PoC (auth bypass)
│   │   ├── hikscript.py               # HIKSCript - ICSA-17-124-01
│   │   ├── backdoor_exploit.js        # BeEF module - backdoor access
│   │   ├── exploiter_checker.py       # HikvisionExploiter checker
│   │   ├── ingram_pro_runner.py       # Ingram-Pro POC runner
│   │   ├── generic_cam_bf.py          # Multi-vendor default creds
│   │   └── hikvision_password_helper_releases.html  # HikPasswordHelper download
│   │
│   ├── canon_vb/                       # Canon VB / WV-HTTP
│   │   ├── vbviewer_bruteforce.py     # Original Canon VB BF
│   │   ├── vbviewer_bf_cve.py          # BF + 6 CVE exploits
│   │   ├── vbviewer_native_bf.py       # Canon-specific auth endpoints
│   │   ├── *_progress.json            # BF progress
│   │   ├── *_results.json             # BF results (unlocked cams)
│   │   └── *.log                      # BF logs
│   │
│   ├── axis/                           # AXIS cams
│   │   ├── axis_bruter.py             # AXIS BF
│   │   ├── axis_rockyou.py            # AXIS + rockyou wordlist
│   │   └── webcamxp_bruter_enhanced.py # WebcamXP 5 (lockout-aware)
│   │
│   ├── dahua/                          # Dahua cams
│   │   └── dahua_bf.py                 # Dahua HTTP + RTSP BF
│   │
│   ├── panasonic/                      # Panasonic i-PRO / BB-HCM
│   │   └── panasonic_bf.py             # i-PRO BF + CVE-2021-32947
│   │
│   └── hipcam/                         # Hipcam / No-IP cams
│       └── hipcam_bf.py                # Hipcam RTSP BF
│
├── protocol_specific/                 # Protocol-level exploits
│   ├── http_basic/                    # HTTP Basic Auth BF
│   │   └── test_credentials.py        # Basic auth test
│   ├── rtsp/                          # RTSP BF (Digest, Basic)
│   ├── onvif/                         # ONVIF device_service exploits
│   └── isapi/                         # Hikvision ISAPI/XML exploits
│
├── exploits/                           # CVE exploits by severity
│   ├── cvss_7plus/                    # (empty - high-CVSS exploits)
│   ├── auth_bypass/                   # (empty - auth bypass)
│   ├── cmd_injection/                 # (empty - cmd injection)
│   ├── cvss7_exploits.py              # Combined CVSS 7+ cam exploits
│   └── vendor_cves.py                  # Per-vendor CVE database
│
├── credentials/                        # Credential lists
│   ├── camera_credentials.txt          # 327 generic cam creds
│   ├── camera_brands_credentials.txt   # Per-brand creds
│   ├── brand_credentials.py            # Brand-specific lookup
│   └── brand_specific_bruteforce.py    # BF using brand creds
│
├── log_files/                          # All BF log files
│
└── progress_files/                     # (move JSON progress here)
```

## Vendors Supported

### Hikvision (vendor_specific/hikvision/)
- **CVE-2017-7921** - Improper Auth bypass via `?auth=YWRtaW46MTEK`
- **HIKSCript** - ICSA-17-124-01 detection
- **HikvisionExploiter** - Auto exploitation checker
- **HikvisionBackdoorExploit** - BeEF integration
- **Ingram-Pro** - 40+ POC scanner
- **HikPasswordHelper** - Decrypt config files
- **Generic BF** - 50+ default credentials

### Canon VB (vendor_specific/canon_vb/)
- **vbviewer_bruteforce.py** - Original Canon VB BF
- **vbviewer_bf_cve.py** - BF + 6 CVE exploits (CVE-2018-6911, etc)
- **vbviewer_native_bf.py** - Tests Canon-specific admin endpoints
- **anon WV-HTTP** - Anonymous streams work without auth

### AXIS (vendor_specific/axis/)
- **axis_bruter.py** - AXIS BF
- **axis_rockyou.py** - AXIS + rockyou wordlist
- **webcamxp_bruter_enhanced.py** - WebcamXP 5 (with lockout)

### Dahua / Panasonic / HiSilicon / i-PRO
- **CVE-2017-7921** - Hikvision auth bypass (CVSS 9.8)
- **CVE-2018-10561/10562** - Dahua auth bypass (CVSS 9.8)
- **CVE-2018-9995** - D-Link auth bypass (CVSS 9.8)
- **CVE-2021-32947** - Panasonic i-PRO URL traversal (CVSS 9.8)
- Run all 4 simultaneously via: `python bruteforce/exploits/cvss7_exploits.py`
- Defaults via `generic_cam_bf.py`
- Vendor-specific: `dahua_bf.py`, `panasonic_bf.py`

## Quick Start

```bash
# Single cam BF
python bruteforce/vendor_specific/hikvision/generic_cam_bf.py 192.168.1.100

# CVE-2017-7921 Hikvision exploit
python bruteforce/vendor_specific/hikvision/cve_2017_7921.py 192.168.1.100

# Canon VB BF
python bruteforce/vendor_specific/canon_vb/vbviewer_native_bf.py

# Mass BF on all master CSV cams
python bruteforce/framework/mass_bf_all.py
```

## Exploit Chain

1. **Discovery**: Find cam IP (Shodan/InternetDB)
2. **Vendor Detection**: Check Server header, HTTP response
3. **CVE-Specific**: Apply CVE-2017-7921, CVE-2018-6911, etc based on vendor
4. **Default Creds**: Try 50+ creds with cooldown
5. **Custom Exploits**: Use HIKSCript or HikvisionExploiter
6. **Config Decryption**: HikPasswordHelper for Hikvision

## CVE Database (2024-2026)

See: `dossier_ruse/bf_results/CVE_DATABASE_2024-2026.md`

## License

For authorized security testing only. Unauthorized access to computer systems is illegal.
