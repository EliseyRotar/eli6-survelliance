# Mission: Discover ALL Webcams & Network Services in Ruse, Bulgaria

## Goal
Find every publicly accessible webcam and interesting network service
in Ruse, Bulgaria (population ~144k, Danube border city with Romania).

## Ruse Quick Facts
- Coordinates: ~43.8564N, 25.9707E
- Country: Bulgaria (BG, .bg)
- Postal codes: 7000-7099
- Local phone: +359 82
- Major ISPs: Bulgarian Telecommunications Company (VIVACOM/BTC), A1 Bulgaria,
  Yettel Bulgaria, Telenor, BulSat, MTel, PowerNet, Cooolbox, Spectrum Net
- Major ASNs: AS8866 (VIVACOM), AS12716 (A1), AS35141 (SFB), AS43270 (SkyLink)
- Border crossings: Giurgiu-Ruse (bridge to Romania), Ruse-Novo Selo (road)

## Approach (in order, parallel where possible)

### Phase 1: Discovery Research
- DuckDuckGo/Google search: "Ruse Bulgaria webcam", "webcam Ruse", "camera Ruse live",
  "Ruse traffic camera", "Ruse CCTV", "kameri Ruse", "ueb kamera Ruse"
- Search Cam-Hack, Insecam, Windy.com, Webcams.travel for Ruse specifically
- Search on tourism sites: visit.ruse.bg, ruseinfo.bg
- Search on city hall, ports, news stations
- Look for local cam aggregators: bulgarian-portal/cameras.bg type sites

### Phase 2: Network Discovery
- Identify Ruse IP ranges (use RIPE/Whois)
- Scan common port ranges on Ruse IPs (HTTP 80/81/88/8080/8443/443,
  RTSP 554/8554, MJPEG 80-10000)
- Use Shodan/Censys/ZoomEye filters: city:"Ruse" or country:"BG" + port:80
- Use Netlas.io OSINT for Ruse-prefixed IPs
- Reverse DNS: cam.ruse.bg, webcam.ruse.bg, *.ruse.bg, *.ruse.eu

### Phase 3: Active Probe
For every Ruse IP found:
1. Probe HTTP/HTTPS/RTSP/MJPEG ports
2. Detect vendor via Server header / WWW-Authenticate realm
3. Try canonical streaming URLs per brand (Axis /onvif/media.amp,
   Hikvision /Streaming/tracks/101, Canon WV-HTTP etc.)
4. If 200 OK + MJPEG/H264 stream -> record it
5. If 401/Auth required -> attempt BF (bruteforce/ folder)

### Phase 4: Bypass Auth (NO FAILURES)
For each protected cam:
1. Try default credentials from `bruteforce/brand_credentials.py`
   (~1000+ combos by brand)
2. Try CVE exploits from `bruteforce/vendor_cves.py`:
   - Hikvision ISAPI: CVE-2017-7921 (auth bypass via /System/configurationFile)
   - Dahua: CVE-2021-33044 (auth bypass)
   - Axis: various
   - HiSilicon: CVE-2021-33244
   - i-PRO/WV: CVE-2021-32947 (MeritIpAddr cookie)
3. Use `ultimate_bruteforce.py` with all 1000 creds x 25 brands
4. Try WebcamXP lockout-aware brute forcer
5. If nothing works, research online for that specific brand/model 0days

### Phase 5: Discovery Beyond Webcams
For each cam IP, also probe:
- HTTP services on alt ports (81, 88, 8080, 8443, 9090, 8000-8100)
- RTSP on 554, 8554
- FTP on 21 (anonymous)
- Telnet on 23
- SNMP on 161 (community 'public')
- SMB on 445
- SIP on 5060 (may have cameras)
- UPnP discovery
- mDNS/Bonjour on 5353 (Apple cams)
- Industrial protocols: Modbus 502, BACnet 47808

### Phase 6: Documentation
For each cam/service found:
- Save samples + HTML snapshots + script output
- Write dossier to `ruse_dossier/` folder
- Map every cam on a city map (lat/lon -> city region)
- Document bypass method used
- Add all to `controllable_Webcams.csv` with city=Ruse, country=Bulgaria

## Tools to use
- `bruteforce/ultimate_bruteforce.py` (1000 creds x 25 brands)
- `bruteforce/brand_credentials.py` (per-vendor creds)
- `bruteforce/vendor_cves.py` (CVE database)
- `camera_testing/cam_sniffer.py` (vendor detection)
- `camera_testing/nvr_scan.py` (NVR/DVR scanner)
- `camera_testing/mass_port_scan.py` (port scan)
- `camera_testing/probe_lib.py` (200+ probe patterns)
- DuckDuckGo/web search for online research

## Deliverables
- Updated `controllable_Webcams.csv` with Ruse cams (city="Ruse", country="Bulgaria")
- `ruse_dossier/` folder with per-cam details
- Map of all discovered cams by location
- Report of which cams required BF (which creds worked)
- Any 0days found

## Rule
DO NOT MODIFY THE EXISTING CSV - only APPEND new cams to it.
Use LF line endings, follow 35-column schema.
