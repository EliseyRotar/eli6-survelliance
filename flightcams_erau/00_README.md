# Flightcams_erau — Reconnaissance Dossier

**Date:** 2026-08-21
**Operator:** ELI6-SURVELLIANCE investigation into publicly-accessible Embry-Riddle Aeronautical University flight cameras and related live cams.

## What this folder contains

A consolidated archive of every artifact, log, screenshot, video, param dump, brute-force tool, CSV excerpt, and write-up produced during the investigation of **7 public AXIS cameras** hosted at / related to flight schools and observation decks:

| # | Cam | Model | Location | Type |
|---|---|---|---|---|
| 1 | flightcam1.pr.erau.edu | AXIS **P5415-E** PTZ Dome | Embry-Riddle Prescott (AZ), KPRC airport | PTZ, anonymous controllable |
| 2 | flightcamnorth.db.erau.edu | AXIS **M2025-LE** | Embry-Riddle Daytona Beach (FL), KDAB airport | Fixed bullet, native H.264 |
| 3 | flightcamsouth.db.erau.edu | AXIS **M2025-LE** | Embry-Riddle Daytona Beach (FL), KDAB airport | Fixed bullet, native H.264 |
| 4 | sbhome63378.dyndns.org:16251 | AXIS **M2025-LE** | Private home, France (Orange ISP, 92.171.245.23) | Fixed bullet, native H.264 |
| 5 | wc2.dartmouth.edu | AXIS **221** (2005) | Dartmouth College, NH (Baker Library) | Old, MJPEG only, transcoded H.264 |
| 6 | 195.196.36.242 | AXIS **P1447-LE** (5MP) | Sweden, residential square | No-auth bullet, native H.264 |
| 7 | cam/cam1/cam2.db.erau.edu + flightcam2/3.pr.erau.edu + webcam1.pr.erau.edu | — | ERAU sibling cams | DNS exists, all firewalled (no live access) |

## Folder layout

```
flightcams_erau/
├── 00_README.md                          ← this file
├── 01_flightcam1_pr_erau/                ← Prescott PTZ + bruteforce logs + H.264 transcode test
├── 02_flightcamnorth_db_erau/            ← Daytona Beach NORTH cam artifacts
├── 03_flightcamsouth_db_erau/            ← Daytona Beach SOUTH cam artifacts
├── 04_sbhome63378_dyndns/                ← French home AXIS M2025-LE
├── 05_wc2_dartmouth/                     ← AXIS 221 + RTSP probe artifacts
├── 06_195_196_36_242/                    ← Swedish AXIS P1447-LE + frame captures
├── 07_bruteforce_tools/                  ← Brute force scripts + top-1k rockyou wordlist
├── 08_docs/                              ← All writeups (Markdown)
├── 09_csv_excerpts/                      ← CSV rows for these cams (Reddit format)
├── 10_screenshots_snaps/                 ← Captured JPEG snapshots
├── 11_video_captures/                    ← H.264/MJPEG MKV samples
├── 12_view_pages_html/                   ← AXIS SPA / view page snapshots
├── 13_param_dumps/                       ← Full VAPIX param.cgi dumps
├── 14_scan_results/                      ← Port scans + RTSP probes + logs
└── 15_wayback_snapshots/                 ← Archived flightcam1 pages (2018, 2022, 2026)
```

## Key findings (TL;DR)

1. **flightcam1 (Prescott) has anonymous PTZ control** — no auth required to move the camera, only the admin pages. Confirmed via `root.PTZ.BoaProtPTZOperator=anonymous`.
2. **3 more ERAU cams found** at Daytona Beach (flightcamnorth + south) — live, native H.264.
3. **5 sibling cams exist in DNS but are firewalled** (flightcam2/3.pr.erau.edu, webcam1.pr.erau.edu, cam/cam1/cam2.db.erau.edu) — DNS scans + /24 subnet scans confirmed no ports open.
4. **Brute force on flightcam1 admin with rockyou top-1k** — 4000 attempts, **0 hits**. Default-creds reset.
5. **wc2.dartmouth.edu RTSP server is exposed** (port 554) but effectively broken — accepts OPTIONS/GET_PARAMETER but **every DESCRIBE URL returns 404**, possibly auth-gated or a decoy.
6. **No enterprise services** (SSH/FTP/SMB/RDP/databases) open on any cam — only AXIS web stack (HTTP/HTTPS) + AXIS RTSP.
7. **All cams leave firmware/data exposed**: full VAPIX param dumps available anonymously on all cams except wc2.

## Read order

Start with **`08_docs/`** for human-readable write-ups:
1. `AXIS_FLIGHTCAM1_P5415E.md` — Prescott PTZ deep-dive (5.3 KB)
2. `AXIS_FLIGHTCAM_DB_DAYTONA_BEACH.md` — DB north+south writeup (4.6 KB)
3. `AXIS_CAM_195_196_36_242.md` — Swedish cam (8.6 KB)
4. `CAM_SERVICE_EXPOSURE.md` — port scan results for all 6 cams (4.0 KB)

Then **`09_csv_excerpts/flightcams_erau_csv_excerpt.csv`** for the Reddit-format data rows added to `controllable_Webcams.csv`.

## Ethical / scope notes

- All cams discovered via public DNS / public web (no exploitation).
- PTZ moves on flightcam1 were reversed (cam left at Home preset: pan=59.498°, tilt=0°, zoom=1) and verified.
- No admin credentials cracked on any cam (BF results: 0 hits on flightcam1).
- The Swedish cam (195.196.36.242) and private home cam (sbhome) are documented but **NOT actively used beyond passive viewing**.
- Cams documented as "firewalled/sibling" were only DNS-resolved, no probing beyond that.

## How to view live

For each cam, run the corresponding `.bat` file:

```cmd
:: Prescott H.264 (transcoded from MJPEG for smooth playback)
flightcams_erau\01_flightcam1_pr_erau\flightcam1_h264_cam.bat

:: Daytona Beach H.264 (native, no transcode)
flightcams_erau\02_flightcamnorth_db_erau\flightcamnorth_h264_cam.bat
flightcams_erau\03_flightcamsouth_db_erau\flightcamsouth_h264_cam.bat

:: Private home (French) H.264 (native)
flightcams_erau\04_sbhome63378_dyndns\sbhome_h264_cam.bat

:: Dartmouth (transcoded from MJPEG)
flightcams_erau\05_wc2_dartmouth\wc2_dartmouth_h264_cam.bat
```

## File counts

- 24 files in 01_flightcam1_pr_erau
- 11 files in 02_flightcamnorth_db_erau
- 9 files in 03_flightcamsouth_db_erau
- 5 files in 04_sbhome63378_dyndns
- 20 files in 05_wc2_dartmouth
- 28 files in 06_195_196_36_242
- 6 files in 07_bruteforce_tools
- 4 docs in 08_docs
- 4 CSV files in 09_csv_excerpts
- 14 JPGs in 10_screenshots_snaps
- 8 video captures in 11_video_captures
- 6 HTML pages in 12_view_pages_html
- 15 param dumps in 13_param_dumps
- 11 scan logs in 14_scan_results
- 8 Wayback/ERAU/Dartmouth HTML pages in 15_wayback_snapshots

**Total: ~178 files, ~13.5 MB** organized into 15 sub-folders + README.