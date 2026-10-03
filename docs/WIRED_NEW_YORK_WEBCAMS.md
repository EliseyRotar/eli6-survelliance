# Wired New York Webcams — Investigation

> URL submitted: `http://wirednewyork.com/webcam/`
> Result: **DEAD** — Frozen since July 2012 (14+ years)
> Date checked: 2026-08-21

## Summary

Wired New York's webcams at the **Orion building (350 W42nd St, NYC)** were famous for showing the Hudson River, Statue of Liberty, Ninth Avenue, and Lincoln Tunnel ramps looking south. The site uses an old Java applet (`CaptureClient.class`) that polls a single static JPEG URL every 30 seconds.

**The cameras died around July 5, 2012** — but the Apache server is still serving the same frozen JPEG file. The server returns `Last-Modified: Thu, 05 Jul 2012 19:59:40 GMT` and the `Content-Length` has not changed since then.

## Camera URLs (all dead)

| Cam | URL | Resolution | Status |
|---|---|---|---|
| 1 | `http://wirednewyork.com/images/webcams/wired-new-york-webcam1.jpg` | 1024×768 | DEAD since 2012-07-05 19:59:40 GMT |
| 2 | `http://wirednewyork.com/images/webcams/wired-new-york-webcam2.jpg` | 640×480 | DEAD since 2012-07-06 00:19:35 GMT |
| 3 | `http://wirednewyork.com/images/webcams/wired-new-york-webcam3.jpg` | 640×480 | DEAD since 2012-07-06 00:19:26 GMT |
| 4 | `http://wirednewyork.com/images/webcams/wired-new-york-webcam4.jpg` | 640×480 | DEAD since 2012-07-04 18:31:15 GMT |

## Pages

- `http://wirednewyork.com/webcam/` — Cam 1 page (Java applet)
- `http://wirednewyork.com/webcam2/` — Cam 2 page
- `http://wirednewyork.com/webcam3/` — Cam 3 page
- `http://wirednewyork.com/webcam4/` — Cam 4 page
- `http://wirednewyork.com/webcam/new-york-live.htm` — Popup that auto-refreshes the JPEG every 30s
- `http://wirednewyork.com/webcams/` — Index page showing all 4

## Camera Equipment

- **StarDot NetCam XL** (camera model) — installed March 2, 2007
- Cam 1 moved to Orion building (350 W42nd St) April 8, 2007
- Cam 1's previous location was 31st floor of Worldwide Plaza (350 W50th St)

## Why it's dead

The Java applet (`CaptureClient.class`) polls a static URL like `../images/webcams/wired-new-york-webcam1.jpg` with the `<param name="delay" value="30" />` parameter (30 second refresh). The server keeps returning the same JPEG with the same `Last-Modified` header from July 2012.

Visual proof the camera is dead:
- Cam 1 image shows **One World Trade Center under construction** (no spire, much smaller than current)
- Cam 1 image shows **pre-Hudson Yards skyline** (no towers at Hudson Yards 30/35/55)
- Image watermark: "**05 Jul 2012 15:59:39 exp 400**"

## How to watch the dead feed

The .bat file `wiredny_cam.bat` opens the JPEG in a PowerShell Windows Forms PictureBox that polls the URL every 30 seconds. You'll see the **same July 2012 image** over and over. There is no live feed.

### Alternative: opening in browser

Just open `http://wirednewyork.com/webcam/new-york-live.htm` — it auto-refreshes every 30s (HTML `<meta http-equiv="Refresh" content="30">`).

## Related dead cameras the site links to

The site's "See Also" section links to EarthCam cams that **may still be live**:
- `http://www.earthcam.com/usa/newyork/timessquare/` — Times Square Cam
- `http://www.earthcam.com/cams/newyork/hudson/` — Hudson River Park Cam

These are EarthCam-hosted and use a different (Flash/JS) player — likely also dead since Flash EOL in 2020, but worth checking.

## Detection methodology

```bash
curl -sI http://wirednewyork.com/images/webcams/wired-new-york-webcam1.jpg
```

Returns:
```
HTTP/1.1 200 OK
Date: Fri, 21 Aug 2026 15:07:41 GMT
Server: Apache
Last-Modified: Thu, 05 Jul 2012 19:59:40 GMT   ← 14+ years old
Content-Length: 147123                          ← never changes
Cache-Control: max-age=2592000
Content-Type: image/jpeg
```

The pattern that flags this as dead:
1. ✅ Server returns 200 (not dead path)
2. ✅ Content-Length stays the same on repeat fetches
3. ❌ Last-Modified is years in the past
4. ❌ JPG watermark confirms the timestamp

## File index

- `wiredny_cam.bat` — opens cam 1 (default), polls JPG every 30s
- `wiredny_cam1.html` — Cam 1 page
- `wiredny_cam2.html` — Cam 2 page
- `wiredny_cam3.html` — Cam 3 page
- `wiredny_cam4.html` — Cam 4 page
- `wiredny_popup.html` — Cam 1 popup page
- `wiredny_webcams_index.html` — All 4 cams index
- `wiredny_cam{1,2,3,4}_sample.jpg` — Frozen JPG samples (proof of death)