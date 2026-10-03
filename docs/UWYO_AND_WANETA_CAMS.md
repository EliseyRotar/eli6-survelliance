# UWyo Cam + Waneta Lake Webcam — what I found

## 1. University of Wyoming cam — http://actbwebcam.uwyo.edu/index.html

**Status: LIVE, verified right now.**

The page is a Stardot NetCamSCD viewer (legacy Java applet, but the
back-end CGIs still work). Two real endpoints:

| URL | Type | Status |
|-----|------|--------|
| `http://actbwebcam.uwyo.edu/nph-jpeg.cgi?0` | single JPEG frame | 200, `image/jpeg`, ~101 KB |
| `http://actbwebcam.uwyo.edu/nph-mjpeg.cgi` | MJPEG stream | 200, `multipart/x-mixed-replace`, ~25 fps |

Decoded stream:
- Resolution: **1296×960**
- Codec: MJPEG Baseline
- Color: yuvj420p (BT.470BG)
- Frame rate: 25 fps

The still frame is also accessible at the same URL — open it in any
browser to see a single image. The MJPEG endpoint is the live feed.

### Use

**Live in your browser**: no direct way — modern browsers don't render
`multipart/x-mixed-replace`. Use `ffplay` instead.

**Double-click `camera_testing/uwyo_cam.bat`** — opens ffplay live with
the UWyo cam (default mode). Or:

```
uwyo_cam.bat watch         REM live ffplay window
uwyo_cam.bat vlc           REM live VLC window
uwyo_cam.bat capture 30    REM save 30s MP4 to Desktop\uwyo.mp4
uwyo_cam.bat snapshot      REM save one JPEG to Desktop\uwyo_still.jpg
```

---

## 2. Waneta Lake Webcam — https://www.wanetawebcam.com/lvafull.html

**Status: OFFLINE.**

The site is still up (Finger Lakes, NY), but the live feed points to a
home server that no longer exists:

- `http://wanetalake.homeip.net:8081/` — connection timed out
- `http://wanetalake.homeip.net:8087/` (underwater cam) — connection timed out

The HTML still embeds an `<applet>` pointing at those URLs, which means
Java applets are needed to view them at all — and those haven't worked in
browsers since 2017.

### Wayback confirmation

`web.archive.org/cdx` only has **one** snapshot of `wanetalake.homeip.net`
(from 2014). The host has been dead for years; the owner probably moved,
replaced their router, or cancelled their home internet and never updated
the static HTML page.

### What still works

`https://www.wanetawebcam.com/` itself still loads — it just shows a
broken image placeholder where the cam used to be. The page also has
"whole-day" and "time-lapse" `.wmv` files linked, but those are old
archives, not live.

### Use

Nothing actionable. If the owner ever spins the cam back up, the URL
would be:

```
http://wanetalake.homeip.net:8081/-wvdoc-01-/LiveApplet/LiveApplet.class
```

…which is a custom Java viewer class. There's no standard MJPEG /
axis-cgi fallback documented in the HTML.

---

## Files saved

| Path | Purpose |
|------|---------|
| `camera_testing/uwyo_cam.bat` | Double-click .bat for live UWyo cam |
| `docs/UWYO_AND_WANETA_CAMS.md` | This file |
