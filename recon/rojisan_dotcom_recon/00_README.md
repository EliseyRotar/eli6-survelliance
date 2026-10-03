# rojisan_dotcom_recon — Investigation Archive

**Date:** 2026-08-21
**Subject:** `http://www.rojisan.com/roj/cam/`
**Verdict:** **The "cam" is a joke** — displays a 1×1 pixel JPG since 2003.

## TL;DR
**No actual webcam.** The site `rojisan.com` is a personal homepage of a photographer (roger wood), running since 2002 on DreamHost shared hosting. The `/roj/cam/` page shows a literal single-pixel JPG that auto-refreshes every15 seconds, as a self-aware joke about the 2000s webcam fad. **Wayback digest unchanged from 2003-2020** — the JPG is the same 630-byte 1×1 file it's always been.

## Folder layout
```
rojisan_dotcom_recon/
├── 00_README.md                  ← this file
├── 01_cam_page/                  ← The "cam" HTML + pixelcam.jpg + Wayback + 404
├── 02_root_site/                 ← Home page + frames
├── 03_blog/                      ← WordPress 5.7.17 dump + sitemap + categories
├── 04_sister_sites/              ← areyoumyhero, stgroup6, heroregistry, brexton, cafeshops, bpbd, dance, photo, etc.
├── 05_portscan/                  ← Port scan results + Wayback CDX
├── 06_wayback/                   ← Wayback historical URLs
├── 07_wordpress/                 ← WP JSON dumps (users, posts, media, search results)
├── 08_docs/                      ← Full writeup (REPORT.md)
└── 09_robots_disallow/           ← robots.txt + restricted paths
```

## What I scanned
- **Network:** 75.119.202.195 — ports 21/22/80/443/587 open (DreamHost shared server), 554 RTSP closed, no AXIS/VAPIX, no MJPEG, no ONVIF, no video endpoints
- **HTTP paths:** ~150 dirs brute-forced — 99% redirect to `missing.php` (no peeking)
- **WordPress:** 2,300+ posts (2003-2026), 44 categories, 1 user (`roj`, gravatar `c121393fdc07b5d3e274e634c79ebcfe`), full sitemap
- **Wayback:** Full historical crawl of `rojisan.com/*` from 2002-2026
- **Sister sites:** 5+ linked domains, none host webcams

## What I found (nothing actionable for cams)
- The 1-pixel JPG (`pixelcam.jpg`, 630 bytes, 1×1 mjpeg) — unchanged 2003-2020
- The cam page HTML (760 bytes, refreshes every15s, points to pixelcam.jpg)
- WordPress blogs with pet eulogies, political commentary, and photography
- Sister sites on same IP: Hero Registry, Brexton Renaissance, CafeShops, etc.

## Read order
1. **08_docs/REPORT.md** — full writeup
2. **01_cam_page/** — the actual "cam" HTML + JPG + Wayback comparison
3. **05_portscan/PORTSCAN_RESULTS.md** — network scan summary
4. **03_blog/** — WordPress dump (cat for cam/webcam references)

## Reproduction
```bash
# Verify the cam is a 1×1 pixel
curl -sL https://rojisan.com/roj/cam/ -o cam.html
curl -sL https://rojisan.com/roj/cam/pixelcam.jpg -o pixelcam.jpg
ffprobe pixelcam.jpg     # shows width=1, height=1

# Port scan
python -c "
import socket
for p in [21,22,25,80,443,587,554,3306,8080,8888]:
    try:
        s = socket.create_connection(('75.119.202.195', p), timeout=2)
        banner = s.recv(128).decode('latin-1', errors='ignore').split(chr(10))[0]
        print(f'{p} OPEN: {banner}')
        s.close()
    except: pass
"
```