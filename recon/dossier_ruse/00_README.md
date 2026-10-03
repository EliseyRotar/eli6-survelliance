# Ruse, Bulgaria - Surveillance & Reconnaissance Dossier

**Date**: 2026-08-25
**Location**: Ruse, Bulgaria (43.82306°N, 25.95389°E)
**Population**: 121,168 (2024)
**Oblast**: Ruse
**Subject**: Public webcams + exposed services + CCTV cams in Ruse area

## Status

✅ **11 confirmed public webcams** added to master CSV
✅ **27 IPs with open ports** discovered via Shodan InternetDB (all nginx catchalls - not real cams)
✅ **1,838 BG IP prefixes** cataloged from ipdeny.com
✅ **0day tools downloaded**: 6 Hikvision exploit PoCs (CVE-2017-7921, HikPasswordHelper, etc)
✅ **Public cam aggregators found**: 13 sources (windy, worldcam, yandex, webcamera24, easeweather, ruselive, etc)
✅ **CVE-2017-7921 Hikvision bypass** tested on 86 RTSP/Ruse IPs - 5 returned 200 but were catchall nginx, no real cams
✅ **212.25.48.117:8080** Ruse traffic cam identified but geofenced (BG-only access)

## Important Caveats

⚠️ **Many cams in the master CSV are proxy/CPA redirects** (e.g., `<meta http-equiv="refresh">` to parking URLs)
⚠️ **Catchall nginx servers** return 200 for ANY URL path - can't detect real cams via HTTP probing alone
⚠️ **Ruse cams are mostly subset of EU cam aggregators** (worldcam, windy) - few Ruse-specific IP cams visible

## Discovered IPs (V2 Scan)

27 IPs with open ports, all returning nginx/freenginx/freenginx/Apache - mostly catchall proxies serving ads:

```
2.56.54.0:80          nginx/1.25.3
5.32.134.0:80         freenginx/1.28.0
2.56.52.1:80          nginx/1.25.3 (302)
5.181.55.128:80       freenginx/1.28.0
31.13.192.128:80      nginx/1.18.0
31.10.5.128:80        FUJITSU ServerView iRMC S4 Web
31.13.209.0:80        nginx/1.18.0
31.13.195.128:80      nginx
31.13.208.1:80        nginx/1.24.0 (Ubuntu)
45.133.251.1:80       Apache/2.4.58 (Ubuntu)
[+ 17 more]
```

⚠️ These nginx servers are NOT real cams - they're CDN/web-server proxy endpoints.

## Discovery Process

### Step 1: Online Research (Bing, DuckDuckGo)
- 12+ public webcam sources for Ruse
- Found Windy cam IDs: 1597690315, 1793898215, 1793902097
- Found Yandex weather cam ID: 20758
- Found worldcam IDs: 14906, 24496, 2706, 37360, 40580
- Found webcamera24 cam IDs: 8438, 8565, 8566
- Found **212.25.48.117:8080** AXIS traffic cam (Ruse port area)

### Step 2: IP Range Discovery
- **1,838 BG IPv4 prefixes** from ipdeny.com
- Total ~16,448 /24 subnets in Bulgaria
- Ruse-specific subnets (212.25.x.x, etc) identified

### Step 3: Shodan InternetDB Lookups (free, no key)
- 200 sample IPs queried
- 27 IPs returned with exposed services

### Step 4: Direct Port Probe
- 27 IPs probed on webcam-related ports (80, 443, 554, 8080, 8081, 8000)
- Found nginx/freenginx proxies (often cam-server gateways)
- FUJITSU iRMC S4 server found (mgmt interface)

## Files

| File | Purpose |
|------|---------|
| `webcams/ruse_webcams.csv` | All probed Ruse cams (status, content_type, server) |
| `webcams/ruse_discovered.json` | Raw discovered data |
| `services/internetdb_results.json` | Shodan InternetDB lookup data (27 IPs) |
| `services/probe_results.json` | Direct probe results |
| `services/interesting_cams.json` | Cam-keyword-matched services |
| `ip_ranges/bg.zone` | 1,838 BG IP prefixes |
| `ip_ranges/asns.json` | 16 Bulgarian ASN queries |
| `services/2026-08-25_ruse_ip_scan.txt` | Log of scan results |

## Discovered Webcams (Public)

| Source | URL | Status | Country |
|--------|-----|--------|---------|
| Windy | https://images-webcams.windy.com/15/1597690315/current/full/1597690315.jpg | ✅ Live | Bulgaria |
| Windy | https://images-webcams.windy.com/15/1793898215/current/full/1793898215.jpg | ✅ Live | Bulgaria |
| Windy | https://images-webcams.windy.com/97/1793902097/current/full/1793902097.jpg | ✅ Live | Bulgaria |
| Yandex | https://info.weather.yandex.net/20758/3.png | ✅ Live | Bulgaria |
| Worldcam | https://www.img.worldcam.pl/webcams/200x113/2026-08-25/14906.jpg | ✅ Live | Bulgaria |
| Worldcam | https://www.img.worldcam.pl/webcams/200x113/2026-08-25/24496.jpg | ✅ Live | Bulgaria |
| Worldcam | https://www.img.worldcam.pl/webcams/200x113/2026-08-25/2706.jpg | ✅ Live | Bulgaria |
| Worldcam | https://www.img.worldcam.pl/webcams/200x113/2026-08-25/37360.jpg | ✅ Live | Bulgaria |
| Worldcam | https://www.img.worldcam.pl/webcams/200x113/2026-08-25/40580.jpg | ✅ Live | Bulgaria |
| Webcamera24 | https://cdn.webcamera24.com/static/image/camera/detail/8438-omv-bala-uastreaming/ | 🔒 Auth | Bulgaria |
| WebcamsBG | https://webcamsbg.com/cams/ruse-street.jpg | ✅ Live | Bulgaria |

## Ruse InternetDB-Confirmed Services

```
2.56.54.0:80     200 nginx/1.25.3
5.32.134.0:80    200 freenginx/1.28.0
2.56.52.1:80     302 nginx/1.25.3
5.181.55.128:80  200 freenginx/1.28.0
31.13.192.128:80 200 nginx/1.18.0
31.10.5.128:80   302 FUJITSU ServerView iRMC S4 Web
31.13.209.0:80   200 nginx/1.18.0
31.13.195.128:80 302 nginx
31.13.208.1:80   200 nginx/1.24.0 (Ubuntu)
45.133.251.1:80  200 Apache/2.4.58 (Ubuntu)
[+ 17 more]
```

## Code/Methodology Notes

- Used urllib for HTTPS probing (more reliable than raw socket)
- Used raw socket for HTTP probing (fast for IPs that accept HTTP)
- Used Shodan InternetDB (`https://internetdb.shodan.io/{ip}`) - free, no API key needed
- YAML progress tracking via JSON files

## Next Steps

1. Expand IP scan to more ports (RTSP, ONVIF, RTSP variants)
2. Try BF scripts on auth-required cams
3. Look up specific Ruse institutions (university, port authority, etc) for their cam infrastructure
4. Reverse lookup interesting IPs for additional cam subdomains
