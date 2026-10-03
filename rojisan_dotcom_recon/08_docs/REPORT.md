# rojisan.com — Reconnaissance Report

**Date:** 2026-08-21
**Operator:** ELI6-SURVELLIANCE investigation into the URL `http://www.rojisan.com/roj/cam/`

## TL;DR

**The "cam" is a joke.** `http://www.rojisan.com/roj/cam/` displays a literal **1×1 pixel JPG** that auto-refreshes every15 seconds. It's been this way **since 2003** (Wayback digest `WJYZ7OQT2QTGYHYGW3HCKFJFS5T7EGJI` unchanged 2003→2020). The image is 630 bytes of MJPEG data, representing a single pixel. There is **no actual webcam** anywhere on rojisan.com — confirmed via:

- Source inspection of the cam HTML page
- Direct download of `pixelcam.jpg` (630 bytes, 1×1 mjpeg)
- Wayback historical snapshots (all identical 2003-2020)
- Deep directory brute (~150 paths tried, all 302→missing.php except `/images/`, `/temp/`, `/roj/`)
- 8x WordPress API searches for "cam", "webcam", "camera" in 2,300+ blog posts (no webcam-related content)
- Inspection of robots-disallowed paths (`/roj/photo/`, `/roj/travel/`, `/roj/music/`, `/roj/pm/`, `/pd/`, `/cgi-bin/mt/`)

## Site identity

- **Owner:** roger wood (username "roj", gravatar `c121393fdc07b5d3e274e634c79ebcfe`)
- **Location:** DreamHost shared hosting (Portland, OR datacenter `apache2-moon.pdx1-shared-a1-43.dreamhost.com`, IP `75.119.202.195`)
- **Domain age:** active since Nov 2002 (first Wayback snapshot 2002-11-22)
- **Stack:** WordPress 5.7.17 (blog), static HTML (frames), old Movable Type (mt) for `/cgi-bin/mt/` (off)
- **WordPress:** 2,300+ posts (2003-2026), 44 categories, 1 user (author "roj", id=2)
- **Sister sites on same IP:** areyoumyhero.com, stgroup6.net, heroregistry.org, brexton.org, cafeshops.com — all linked from the home page

## The "cam" page

`https://rojisan.com/roj/cam/` (HTTP 200, 760 bytes, Last-Modified: Sun, 02 Sep 2007 13:00:00 GMT)

Source:
```html
<HTML>
<HEAD>
<TITLE>Cam</TITLE>
<meta http-equiv="refresh" content="15">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="expires" content="now">
</HEAD>
<BODY BGCOLOR="#000000" text="FFFFFF" link="CC33CC" vlink="7777FF" alink="0000EE" topmargin="0" leftmargin="0">
<font face=arial>
<font size=3>
<center>
<p>
<p>
<P><B>rojisan's 1-pixel webcam</B>
<font size=2>
<p>
<p>
<br>&nbsp;v
<br>>&nbsp;<img src="pixelcam.jpg">&nbsp;<
<p>
<p>
[ 15-second refresh ]
<br>enjoy!
</center>
</BODY>
</HTML>
```

The image:
- URL: `https://rojisan.com/roj/cam/pixelcam.jpg`
- Size: **630 bytes**
- Format: JPEG (magic bytes `FF-D8-FF-E0`, JFIF)
- Dimensions: **1×1 pixel**
- Codec: mjpeg, profile Baseline
- Last-Modified: Sun, 02 Sep 2007 13:00:00 GMT (the JPG file itself, not just the page)

## What this site actually is

`rojisan.com` is the personal homepage of **roger wood**, a **photographer** specializing in **belly dance performance photography**. The site has been continuously maintained since 2002 with:

- Performance photography galleries (`/photo/`)
- Dance community resources (`/dance/`)
- "Basic Production for Belly Dance" blog (`/bpbd/`) - WP 5.7.17
- "What is your belly dance color?" quiz (`/dancercolor/`)
- push-back spam blog (`/spam/`) - shut down due to SLAPP lawsuit in Canada
- A "1-pixel webcam" joke page (`/roj/cam/`)
- A personal meta-blog (`/blog/`) - WP 5.7.17, 2,300+ posts 2003-2026

The 1-pixel webcam is a self-aware joke about the early-2000s webcam fad — when many people set up low-quality personal webcams showing mundane daily life, this page satirizes that trend by showing literally one pixel.

## Network & services

### Open ports (from ~340 port scan)
- **21** FTP — DreamHost FTP (server-wide)
- **22** SSH — OpenSSH 9.6p1 Ubuntu (server-wide)
- **80** HTTP — Apache, redirects to HTTPS
- **443** HTTPS — Apache with valid cert for rojisan.com
- **587** SMTP submission — DreamHost mail (server-wide)

### Closed/filtered
All other ports (25, 3306, 5432, 8080, 8443, 8888, 27017, 50000, etc.) timeout. This is a **shared hosting server** — no dedicated resources, no SSH/FTP specific to rojisan.

### Sibling sites (same IP, all linked from rojisan home)
- **areyoumyhero.com** — Hero advocacy org
- **stgroup6.net** — The Hero Registry
- **heroregistry.org** — Hero registry
- **brexton.org** — Brexton Renaissance (charity)
- **cafeshops.com** — CafeShops (commercial)

None of these host webcams either.

## What I searched but didn't find

- **No webcam endpoints** anywhere on the site (no `/mjpg/`, `/axis-cgi/`, `/video.cgi`, `/webcam.jpg`, `/nowcam.jpg`, `/capture.jpg`, `/live.sdp`, etc.)
- **No ONVIF / RTSP** server (port 554 not open)
- **No MJPEG/AV1 endpoints** 
- **No IP camera admin pages** (no `/admin/`, `/operator/`, `/index.html`, no `Dahua/AXIS/Hikvision/Vivotek` fingerprints)
- **No real cam** in any blog post (2003-2026 archives, 2,300+ posts, WordPress JSON search returned no webcam-related content)
- **No cams in sister sites** (bpbd blog, dancercolor quiz, dance page, photo galleries, spam blog all have no video/streaming)

## Files saved

| Folder | Contents |
|---|---|
| 01_cam_page/ | The "cam" HTML, pixelcam.jpg, Wayback snapshot of cam page |
| 02_root_site/ | Home page + frame structure |
| 03_blog/ | WordPress blog dump + sitemap + JSON search results |
| 04_sister_sites/ | areyoumyhero, bpbd, dancercolor, photo, etc. |
| 05_portscan/ | Port scan results + Wayback CDX |
| 06_wayback/ | Wayback historical URLs |
| 07_wordpress/ | WordPress user/media/post JSON |
| 08_docs/ | This writeup |
| 09_robots_disallow/ | robots.txt + restricted paths |

## Verdict

`http://www.rojisan.com/roj/cam/` is **not a real webcam**. It is a **22-year-old art piece / joke page** showing a single pixel that auto-refreshes every15 seconds. The site is a personal photographer's homepage and blog, not a webcam host. **Nothing actionable** for cam reconnaissance.

## Notes / eth
- No creds cracked, no exploits attempted, no admin pages probed with auth.
- All traffic is public web — robots.txt + sitemap are public.
- Wayback fetching is for archival pages (already public on web.archive.org).
- WordPress user enumeration is a known public WP behavior (no exploit involved).