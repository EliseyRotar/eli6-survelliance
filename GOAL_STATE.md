# ELI6 SURVEILLANCE - Project Goal & State

## Goal
- **Make every fl511.com cam display a LIVE MOVING VIDEO** (HLS .m3u8 + .ts/.mp4 segments OR MJPEG); static placeholder NOT acceptable.
- **Expand coverage**: Houston TranStar (DONE, JPEG-only), SATAP A4 Italy (DONE), webcams.aeroclubea.com Kenya (DONE), AZ511 (DONE, JPEG-only), 511 NY (DONE, 1,866 cams), Africam worldwide (DONE, 34 cams), OpenCCTV (DONE, 33,510+ cams, 7,000+ verified live HLS), Argus cleanup (DONE, 60k cams).

## Progress

### Session 20-27 (Sep 5-12) - fl511 LIVE + 6 other sources
- fl511 LIVE HLS via xflow.m3u8 (4,555 cams, 528 xflow cache, 535+ brute-forced)
- Houston TranStar: 2,312 cams (JPEG-only, slideshow API)
- SATAP A4: 12 cams (MP4 byte-range proxy)
- Kenya Webcam: 153 cams (MJPEG)
- AZ511: 644 cams (JPEG-only, no live)
- 511 NY: 1,866 cams (1,561 HLS + 305 static JPEG)
- Africam: 34 cams (YouTube embeds)
- OpenCCTV: 33,510 cams (~7,000+ live HLS verified)

### Session 28 (Sep 12) - Argus name cleanup + more OpenCCTV
- **argus_cleanup_v2.py**: 51,105 argus names improved using URL patterns + 80+ operator name mappings
- **argus_cleanup_v3.py**: 40,824 messy URL-derived names cleaned (e.g. "ALERTCalifornia Cam 0" instead of "https: cameras.alertcalifornia.org ALERTCalifornia 0 .jpg")
- **opencctv_extra_v2.py**: fetched 70+ countries, 20 pages each = 9,971 new cams discovered
- **opencctv_extra_v2_ingest.py**: 4,606 truly unique cams ingested
- **fix_dup_idxs.py**: 2,270 duplicate idxs resolved (renumbered 258086-260355)
- **fix_live_status.py**: 11 bad live_status values fixed (was 'Marion Township', '200', etc.)
- **Reaper restarted** to pick up 251,900 new rows (was 205,944)
- **(argus) text fully removed** from names/descriptions/notes

### Final Session 28 stats
- **251,826 total cams** in CSV/DB
- **225,910 live** (89.7%)
- **65,754 HLS + 7,122 MP4 + 3,840 YouTube + 174,664 MJPEG**
- 181 countries, 32,119 cities, 2,900 hosts
- Top countries: US 92,083, Japan 20,364, Taiwan 13,361, Canada 9,522, S. Korea 8,731

### Backups (in `backups/`)
- `backup_20260912_015741` (171MB CSV + 721MB DB) - after argus v2/v3
- `backup_20260912_015945` (171MB CSV + 721MB DB) - after OpenCCTV extra
- `session_v15_20260912_020300/` (7 key files)
- Earlier: backup_20260912_000521, backup_20260912_012701, backup_20260912_013646, backup_20260912_014532

## Background processes still running
- **argus_geocode.py** (PID 28156): 1,000+ cached, 1 req/sec, ~12-17hr remaining for 60k argus cams
- **cam_reaper.py** (PID 24772): restarted, probing 45,940 new URLs
- **fl511_token_daemon.py** (PID 16552): refreshing divas tokens
- **dashboard** (PID 20020), **fl511 HLS proxy** (12964), **Skyline** (23840), **Digitraffic** (17376)

## Next steps
- Wait for argus geocode to enrich more roads/cities
- Let cam_reaper clean up the 45,940 new rows
- Continue enriching argus names with URL patterns (if user requests)
