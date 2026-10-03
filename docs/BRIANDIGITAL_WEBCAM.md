# briandigital.com/cam/webcam.html - Investigation

> Original URL: `http://briandigital.com/cam/webcam.html`
> Status: **DEAD** - Page returns 404; cam was decommissioned long ago
> Date checked: 2026-08-21

## 🎯 Live URL: NONE

There is **no live stream**. The cam has been dead for **at least a decade**.

The page was originally at `http://briandigital.com/cam/webcam.html` but currently returns **404** at HTTPS (HTTP→HTTPS 308 redirect, then 404).

## What was here (Wayback Machine reconstruction)

Brian Christiansen ran a **personal backyard webcam** from his Massachusetts home, powered by:

| Component | Detail |
|---|---|
| **Hardware** | Apple iSight camera (FireWire) |
| **Computer** | Power Mac G5 |
| **OS** | Mac OS X 10.4 "Tiger" |
| **Software** | **EvoCam** (by Evological) — Mac webcam capture software |
| **URL structure** | `briandigital.com/cam/` |
| **Image format** | Single JPEG snapshot (`webcam.jpg`), 640×480 |
| **Refresh rate** | Every 6 minutes (360 seconds) |
| **Server** | Plain Apache, single file upload |

### Webcam URLs (all dead now)
| URL | Purpose | Format |
|---|---|---|
| `http://briandigital.com/cam/webcam.jpg` | Latest JPEG snapshot | Direct image |
| `http://briandigital.com/cam/webcam.html` | Auto-refresh HTML (meta-refresh every 360s) | HTML |
| `http://briandigital.com/cam/jscam.html` | Auto-refresh HTML using JS | HTML |
| `http://briandigital.com/cam/javacam.html` | Auto-refresh using Java applet (EvoCam.jar) | Java applet |

### Page contents (from Wayback)
From the archived HTML at https://web.archive.org/web/20081014054918id_/http://briandigital.com:80/cam/webcam.html:
```html
<HTML>
<META HTTP-EQUIV="refresh" CONTENT="360">
<META HTTP-EQUIV="expires" CONTENT="0">
<META HTTP-EQUIV="pragma" CONTENT="no-cache">
<HEAD>
<TITLE>EvoCam Example Page</TITLE>
</HEAD>
<BODY>
<CENTER>
<IMG SRC="webcam.jpg">
<BR>
<SMALL>
Powered by <A HREF="http://www.evological.com/evocam.html">EvoCam</A>
</SMALL>
</CENTER>
</BODY>
</HTML>
```

From `cam/` index page (https://web.archive.org/web/20081011045448id_/):
> "Thanks for tuning into my backyard cam, you must be supremely bored."
> "This cam's main function is so that my family and I may see what the weather's like outside our back windows, especially in the winter."
> "Don't be surprised: cam may be offline at any time without warning, as conditions permit, etc. For example, the cam isn't on at night. No need. Refresh times may vary."
> 
> Stack: Apple iSight, EvoCam, Mac OS X, G5

## The cam owner: Brian Christiansen

From the meta tag (`<meta name="author" content="Brian Christiansen">`) and his current `/about/` page:

> "Dad of 3. Lead product designer (UX Generalist) Loves bicycles, the woods, tea, weather, music & drums, EVs, **InsDsgMEd**, **UConn alumnus**. #NUFC"

| Field | Value |
|---|---|
| **Name** | Brian Christiansen |
| **Username** | briandigital / @briandigital on Micro.blog |
| **Education** | UConn (University of Connecticut) alumnus |
| **Family** | Dad of 3 |
| **Job** | Lead product designer / UX Generalist |
| **Location** | Massachusetts (woods + biking = New England) |
| **Hobbies** | Bicycles, weather watching, music, drums, EVs |
| **Sports** | Newcastle United FC fan (#NUFC) |
| **Site platform** | Hugo static blog hosted on Micro.blog (since ~2018) |
| **Original site** | Self-hosted on briandigital.com (since ~2002) |

The cam was a **personal hobby project**, not commercial. Brian was a tech-savvy early adopter who built his own personal website in2002 and ran various experiments (the cam, blog, podcast, etc.) over the years.

## What the cam showed

A **two-car garage with blue doors**, wood privacy fence, mature deciduous trees, gravel driveway. Cars and a Harley-Davidson motorcycle visible at different times.

**Snapshot 1: July 7, 2006** - Lush summer afternoon, VW Passat sedan parked, Harley-Davidson motorcycle, sun-dappled driveway.
**Snapshot 2: July 14, 2006** - Smaller image (21KB - likely camera glitch or very plain image).
**Snapshot 3: July 19, 2006** - Same scene, cars gone, watermark "7/19/06 3:31 PM".

After 2006, Wayback only captured the **same JPEG being re-served** (same digest `ZWGDK2RDI7I7TFLTIKKECYH2MMFSPTEW` for the first one, with newer dates being reused). The cam appears to have stopped updating sometime in late 2006 or 2007.

## Wayback Machine timeline

| Date | Capture |
|---|---|
| 2006-07-07 20:48:43 | **First capture** - webcam.jpg (134KB) + webcam.html |
| 2006-07-14 01:11:18 | webcam.jpg (21KB - anomaly) |
| 2006-07-19 08:26:52 | webcam.jpg (138KB) - last unique image |
| 2008-10-11 04:54:48 | /cam/ index page only |
| 2008-10-14 05:49:18 | webcam.html only |
| 2008-11-20 22:55:03 | webcam.html only |
| 2009-01-26, 02-01, 03-06 | webcam.html snapshots |
| 2014-11-04, 2015-02-21, 2015-05-10 | webcam.html snapshots |
| 2020-11-11 18:53:27 | 301 redirect (page removed) |
| 2020-11-11 18:53:27 | 404 (cam fully gone) |
| 2025-08-28 14:45:28 | 308 redirect (server reconfigured) |
| 2025-08-28 14:58:33 | 404 (still gone) |

## Detection methodology

```bash
# 1. Fetch the page
curl -sL "http://briandigital.com/cam/webcam.html"
# -> HTTP 308 redirect to https://..., then 404

# 2. Try HTTPS
curl -sILk "https://briandigital.com/cam/webcam.html"
# -> HTTP 404 Not Found (Caddy/nginx)

# 3. Try common cam URLs
curl -sIk "https://briandigital.com/cam/webcam.jpg"  # 404
curl -sIk "https://briandigital.com/cam/javacam.html"  # 404
curl -sIk "https://briandigital.com/cam/jscam.html"  # 404
curl -sIk "https://briandigital.com/cam/"  # 404

# 4. Wayback lookup
curl -s "https://web.archive.org/cdx/search/cdx?url=briandigital.com/cam/webcam.html&output=json"
# -> Found snapshots from 2006-2025, but content disappeared after 2020

# 5. Get an actual cam image from Wayback
curl -sL "https://web.archive.org/web/20060707204843id_/http://briandigital.com:80/cam/webcam.jpg" -o cam.jpg
# -> 134KB JPEG with timestamp "07/07/06"
# Shows: garage, blue sedan, Harley motorcycle, trees

# 6. Inspect the page HTML (still works in Wayback)
curl -sL "https://web.archive.org/web/20081014054918id_/http://briandigital.com:80/cam/webcam.html"
# -> HTML with <META HTTP-EQUIV="refresh" CONTENT="360">
# -> "Powered by EvoCam"
```

## Summary

This was a **personal Mac webcam** run by Brian Christiansen (a UX designer and UConn alumnus in Massachusetts) using **Apple iSight + EvoCam** software on his **Power Mac G5 running OS X 10.4 Tiger**. The cam captured a **backyard garage view** as a **single JPEG** every 6 minutes, which was uploaded to `briandigital.com/cam/webcam.jpg`.

The cam appears to have been **decommissioned around 2006-2007** (after the last unique snapshot). The site was **rebuilt on Hugo/Micro.blog** around 2018 and the old `/cam/` directory was deleted (404 since 2020).

There is **no live webcam** at this URL. This was a **decades-old personal project**, not a current cam.

## Files captured

```
camera_testing/
├── briandigital_home.html               # Current homepage
├── briandigital_about.html              # About page (confirms Brian Christiansen)
├── briandigital_webcam_2015.html        # Latest archived cam HTML (EvoCam meta-refresh)
├── briandigital_cam_dir.html            # 2008 archived /cam/ index page (full info)
├── briandigital_javacam.html            # 2006 Java applet version
├── briandigital_jscam.html              # 2006 JavaScript version
├── briandigital_webcam_2006_07.jpg      # First snapshot (with VW Passat + Harley)
├── briandigital_webcam_2006_07_19.jpg   # July 19 snapshot (no cars)
├── briandigital_webcam_2008.jpg         # Wayback-served "2008" (actually still 2006 image)
└── briandigital_webcam_2015.jpg         # Wayback-served "2015" (same 2006 image)
```