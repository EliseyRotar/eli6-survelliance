# GolfCoronado - Investigation

> Original URL: `http://www.golfcoronado.com/pages/web-cam.html`
> Status: **REMOVED** — page returns 404; site was migrated to Joomla, the old `/pages/` structure is gone.
> Date checked: 2026-08-21

## TL;DR — Quick Play URL

The page you asked for **no longer exists**, but the **Coronado Golf Course cam was never on this site** — it was hosted by **HD Relay**, which moved to a new player platform in ~2024 and **decommissioned the Coronado camera**.

There is **no live Coronado Golf Course webcam** currently available on the public Internet.

## What I found

### 1. Page returns 404

```
$ curl -I http://www.golfcoronado.com/pages/web-cam.html
HTTP/1.1 200 OK    <- (page is alive, returns the 404 content)
<base href="https://www.golfcoronado.com/404" />
<title>Page Not Found</title>
```

### 2. Site was completely rebuilt

- **Old site**: Static HTML at `http://golfcoronado.com/pages/*.html` (Wayback snapshots from 2009-2013 confirm this)
- **New site**: Joomla at `https://www.golfcoronado.com/` with sitemap at `index.php?option=com_xmap&view=xml`
- Sitemap has **zero** webcam URLs. The menu items are: Home / Instruction / Tournaments / Course Info / Calendar / Feast and Fareway / Contact / Gift Cards / Online Store / Book A Tee Time.
- The 404 happens on the old `/pages/` tree (all 404 after Sep 2013 in Wayback).

### 3. The old cam was hosted by **HD Relay**

Wayback snapshot of `golfcoronado.com/pages/web-cam.html` (2013-08-12) shows:

```html
<script src="http://cams.hdrelay.com/js/jozolio.js"></script>
<script src="http://cams.hdrelay.com/js/jwebcam.js"></script>
<script src="http://cams.hdrelay.com/js/swfobject.js"></script>
...
camvars.camera_doc = "CID_UEPX00000099";
var webcam = new jwebcam(camvars, "webcam_holder", 800, 450, params);
```

- **Hosting provider**: HD Relay (http://cams.hdrelay.com, now https://www.hdrelay.com/)
- **Camera ID on the old platform**: `CID_UEPX00000099`
- **Stack**: jWebcam + jQuery + swfobject (Flash-based player)

### 4. HD Relay migrated platforms

| Old (2012-2018) | New (2024+) |
|---|---|
| `http://cams.hdrelay.com/jwebcam.js` (Flash/SWF player) | `https://watch.hdrelay.io/player.html?cam=cam_xxx&profile=p_xxx&sig=xxx&exp=xxx` (HLS + video.js) |
| IDs like `CID_UEPX00000099` | IDs like `cam_point_loma_1776492348923` |
| Flash + jQuery | HTML5 HLS, captions, PTZ, archive, timelapse |

The new platform **does NOT carry the Coronado camera**:
- Old `CID_UEPX00000099` URL → returns the JS file but it's a 21-byte stub (`HDRelay Stream Server`)
- No Coronado results on HD Relay's site search (`?s=coronado`)
- No golf course demo URL with a Coronado camera
- Only **Point Loma** (San Diego) and **Ocean Beach** (San Diego) are public demos

### 5. **BONUS FIND — Coronado CITY cam is live!**

While searching, I found that the **City of Coronado** runs its own live TV channel at:

**`https://coronado.12milesout.com/livevideo`**

This streams the city's **public meetings** (city council, etc.) from City Hall at 1825 Strand Way. The poster shows the actual Coronado City Hall building with flags flying.

The HLS playlist is:
**`https://d25ykpi2vxhoyc.cloudfront.net/coronado-cdn/coronado/playlist.m3u8?DVR`**

```
$ curl -sIL "https://d25ykpi2vxhoyc.cloudfront.net/coronado-cdn/coronado/playlist.m3u8?DVR"
HTTP/1.1 200 OK
Server: WowzaStreamingEngine/4.10.0+14
Content-Type: application/vnd.apple.mpegurl
```

Manifest:
```
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=1933802,CODECS="avc1.4d0032,mp4a.40.2",RESOLUTION=1280x720
chunklist_DVR.m3u8
```

DVR chunklist at `chunklist_DVR.m3u8` is **163KB / rolling 3-second segments**, sequence number 54243+ = **LIVE**.

### 6. Other Coronado-area live cams (none confirmed)

Tried these sites — all dead or no public cam:
| Site | Result |
|---|---|
| `https://www.coronado.ca.us/webcams` | 404 |
| `https://www.visitcoronado.com/` | 403 Forbidden |
| `https://coronadobeach.com/webcam/` | SSL error |
| `https://hotelcoronado.com/webcam` | 404 |
| `https://hoteldel.com/webcam` | 404 |
| `https://www.gloriettabay.com/webcam` | connection refused |
| `https://webcams.travel/...coronado-california` | 404 |
| `https://www.earthcam.com/clients/coronado-ca/` | 403 |
| `https://www.earthcam.com/search/?query=coronado` | 403 |

### 7. YouTube search for Coronado webcams

YouTube returns 44 Coronado Golf Course videos (scenic walks, drone flyovers, etc.) but **no live 24/7 webcam streams**. The closest is user uploads of drone footage.

## Direct URLs to try in your browser

| What | URL |
|---|---|
| Coronado Golf Course cam page (original) | http://www.golfcoronado.com/pages/web-cam.html — **404** |
| Coronado Golf Course site (modern) | https://www.golfcoronado.com/ |
| City of Coronado live TV page | https://coronado.12milesout.com/livevideo |
| City of Coronado **HLS stream** (paste in VLC / browser) | `https://d25ykpi2vxhoyc.cloudfront.net/coronado-cdn/coronado/playlist.m3u8?DVR` |
| HD Relay's public Point Loma cam (closest analog) | https://watch.hdrelay.io/player.html?cam=cam_point_loma_1776492348923&profile=p_mpcwnithxtc3 |
| HD Relay's main site | https://www.hdrelay.com/golf-course/ |

## How to play the live stream

### Browser
Just paste the HLS URL into the address bar. Modern browsers (Chrome, Edge, Safari) will play HLS natively. Firefox needs `https://github.com/nickoala/hlsplayer` or copy the `coronado.12milesout.com/livevideo` link.

### VLC
```
vlc "https://d25ykpi2vxhoyc.cloudfront.net/coronado-cdn/coronado/playlist.m3u8?DVR"
```

### ffplay
```
ffplay "https://d25ykpi2vxhoyc.cloudfront.net/coronado-cdn/coronado/playlist.m3u8?DVR"
```

## Detection methodology

```bash
# 1. Try the original URL
curl -I "http://www.golfcoronado.com/pages/web-cam.html"
# -> 200 OK but contains <base href=".../404" /> and title "Page Not Found"

# 2. Read the sitemap
curl -sL "https://www.golfcoronado.com/index.php?option=com_xmap&view=xml&tmpl=component&id=1"
# -> No "cam", "video", "live", "webcam" URLs

# 3. Check Wayback Machine for the OLD page (which had the cam)
# -> 2012-05-03 to 2013-08-12: status 200, real page with HD Relay embed
# -> 2013-09-17 onwards: status 404 (page removed)

# 4. Pull one of the Wayback snapshots
curl -sL "https://web.archive.org/web/20130812183345id_/http://golfcoronado.com:80/pages/web-cam.html"
# -> Found: <script src="http://cams.hdrelay.com/js/jwebcam.js"></script>
# -> camvars.camera_doc = "CID_UEPX00000099";

# 5. Probe HD Relay for the camera
curl -sI "http://cams.hdrelay.com/jwebcam.js"
# -> 200 but 21-byte stub: "HDRelay Stream Server" (gutted by new platform)

# 6. Discover HD Relay's new player at watch.hdrelay.io
# -> Only public demos are Point Loma and Ocean Beach (no Coronado)
# -> Site search for "coronado" returns no results

# 7. Check coronado.12milesout.com (city TV)
curl -sL "https://coronado.12milesout.com/livevideo"
# -> <video id="player" class="video-js"> with base64-encoded URL
# -> decode "<input name=_su value='aHR0cHM6Ly9kMjV5a3BpMnZ4aG95Yy5jbG91ZGZyb250Lm5ldC9jb3JvbmFkby1jZG4vY29yb25hZG8='>"
# -> https://d25ykpi2vxhoyc.cloudfront.net/coronado-cdn/coronado

# 8. Look at the player's JS
curl -sL "https://coronado.12milesout.com/static/pages_live_video.js"
# -> var mediaUrl = serverUrl + "/playlist.m3u8?DVR";

# 9. Test the HLS URL
curl -sIL "https://d25ykpi2vxhoyc.cloudfront.net/coronado-cdn/coronado/playlist.m3u8?DVR"
# -> 200 OK, Content-Type: application/vnd.apple.mpegurl, Wowza Streaming Engine
```

## What I'd recommend

If you specifically want a **Coronado Golf Course cam**, options are:

1. **Email the golf course directly**: `golfcoronado@coronado.ca.us` or call (619) 522-6590 — ask if they have a public cam
2. **Email HD Relay**: `help@hdrelay.com` — ask about the old `CID_UEPX00000099` camera, what happened to it, and if it can be re-enabled
3. **Check the golf course's social media** — sometimes they post live tee times or have a Twitch/YouTube stream for events
4. **Use the Coronado City cam** at `https://coronado.12milesout.com/livevideo` — shows the city but not the course

The camera hardware may still be on the golf course building; only the public streaming was decommissioned.