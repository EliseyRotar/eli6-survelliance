# Big Sky Resort Live Cams (Montana) + Gautefall Dead Cams (Norway)

## Summary

After auditing two Reddit entries from the original `controllable_Webcams.csv` that had been marked dead in the v2 probe (`bigskyresort.com` and `gautefall.no`), I found that:

| Cam | Status | Stream URL |
|-----|--------|-----------|
| **Big Sky Resort Lone Peak Tram Cam** | ✅ LIVE | `https://www.youtube.com/watch?v=6iW7bdSavUo` |
| **Big Sky Resort Everett's 8800 Cam** | ✅ **LIVE NOW (1 viewer)** | `https://www.youtube.com/watch?v=dMr-Jt_K3Cc` |
| **Big Sky Resort Golf Course Cam** | ✅ LIVE | `https://www.youtube.com/watch?v=F067K8BIhbY` |
| **Gautefall Ski Resort — Rytterspranget** | ❌ Host down / firewalled | (was: `http://92.220.126.164:50002/`) |
| **Gautefall Ski Resort — Gautefall Express** | ❌ Host down / firewalled | (was: `http://92.220.126.164:50001/`) |

---

## 1. Big Sky Resort — Montana

### Discovery path

The original Reddit entry pointed to:
```
http://www.bigskyresort.com/Photos-Videos/Webcam.asp
```
That URL returns **404 Not Found** — the resort moved off the legacy `.asp` and rebuilt everything on Next.js (`/current-conditions/webcams`).

The new page at `https://www.bigskyresort.com/current-conditions/webcams` embeds **5 live cams** via iframes:

```html
<iframe src="https://camstreamer.com/embed/hcsmYlCWjirEU86zfXwaFGyX7w6GL3xJ3M3TkbZf?..." title="Lone Peak Tram Camera">
<iframe src="https://camstreamer.com/embed/dmy0fkeL3LXtkQnzlK5Td1QrVGSt08aM8IVVmE08?..." title="Everett's 8800 Camera">
<iframe src="https://camstreamer.com/embed/bvRmCc5qmXcMEJ02xMlIAL4cg3291Tfj0pzIp9tW?..." title="Golf Course Camera">
<iframe>... title="Cascade Camera"  (cameraId=92, clientId=1615936779)
<iframe>... title="Andesite Camera" (cameraId=90, clientId=1615936779)
```

### CamStreamer → YouTube Live unwrap

CamStreamer (`https://camstreamer.com`) is an Axis partner app that proxies Axis camera feeds → YouTube Live. Their embed iframe is just a wrapper around a YouTube player. The CamStreamer IDs (43 chars, e.g. `dmy0fkeL3LXtkQnzlK5Td1QrVGSt08aM8IVVmE08`) are *not* YouTube video IDs — they're CamStreamer's own routing tokens.

The real YouTube Live video IDs are on Big Sky's official channel (`@BigSkyResort`, channel ID `UCU9B-ElyehvxMqNYbNWrvFQ`). I confirmed via the YouTube OEmbed API:

| Cam | YouTube Video ID | Channel |
|-----|------------------|---------|
| Lone Peak Tram Cam | `6iW7bdSavUo` | @BigSkyResort |
| Everett's 8800 Cam | `dMr-Jt_K3Cc` | @BigSkyResort |
| Golf Course Cam | `F067K8BIhbY` | @BigSkyResort |

So **you can watch the streams directly via `https://www.youtube.com/watch?v=<videoId>`** — no CamStreamer needed. The `Everett's 8800 Cam` was actively live at probe time with **1 viewer**.

### Watch live

Open any of these in a browser:
- `https://www.youtube.com/watch?v=6iW7bdSavUo`
- `https://www.youtube.com/watch?v=dMr-Jt_K3Cc`
- `https://www.youtube.com/watch?v=F067K8BIhbY`

Or just double-click:
```
camera_testing\bigsky_cam.bat          REM default = Everett's 8800 Cam (LIVE)
```

### `.bat` modes

```
bigsky_cam.bat              REM Everett's 8800 (default = live ffplay)
bigsky_cam.bat everett      REM Everett's 8800 Cam
bigsky_cam.bat lone         REM Lone Peak Tram Cam
bigsky_cam.bat golf         REM Golf Course Cam
bigsky_cam.bat watch        REM explicit live mode
bigsky_cam.bat vlc          REM open in VLC
bigsky_cam.bat capture 30   REM save 30s MP4 to Desktop\bigsky_cam.mp4
bigsky_cam.bat snapshot     REM save one JPEG to Desktop\bigsky_cam.jpg
```

---

## 2. Gautefall Skisenter — Drangedal, Norway

### Discovery path

The original Reddit entry pointed to:
```
http://www.gautefall.no/Webcam.aspx?ID=323
```
Returns **404** — they rebuilt on WordPress (`/webkamera/`). The current cam page at `https://gautefall.no/webkamera/` lists two Mobotix IP cameras:

```html
<p><a href="http://92.220.126.164:50002/view/index.shtml">Rytterspranget</a></p>
<p><a href="http://92.220.126.164:50001/view/index.shtml">Gautefall Express</a></p>
```

### Mobotix cameras

Both at `92.220.126.164` (Norwegian residential/business IP, owned by Altibox / Tafjord Møre). Port 50001/50002 is a **Mobotix** camera default port.

The standard Mobotix CGI endpoints (`/cgi-bin/image.jpg`, `/cgi-bin/faststream.jpg`, `/stream/mxpeg.cgi`, `/control/imgstream.jpg`) all timed out from my probe location.

### Why it's dead

Several possibilities:
- **Seasonal**: Norwegian ski resort. The cams are probably only powered on during winter ski season (Nov–April). My probe was 21 August — off-season.
- **NAT/firewall**: The residential IP may not be publicly reachable for video streams even when the cams are on.
- **Offline**: The home/business connection may have been cancelled.

I cannot reach the cams from my probe host. **No alternate URL or aggregator mirror found.**

### Worth re-probing in winter

If you're interested, re-probe in November. The `view/index.shtml` page loads a Java applet viewer that should give a visual; if it doesn't load either, the cam is fully offline.

---

## 3. Big Sky CamStreamer detail (for the record)

CamStreamer is **Axis Communications partner software** that runs on Axis IP cameras. It streams the cam feed to YouTube Live, Twitch, Vimeo, etc. and provides a privacy-friendly iframe wrapper so visitors don't need to install anything.

`https://camstreamer.com/embed/<hash>` → loads a YouTube iframe internally. The YouTube iframe ID is stored server-side in CamStreamer's database, not derivable from the hash. So to find the real YT video ID, you have to:
- Crawl the parent page that embeds it (the page embeds BOTH CamStreamer iframes AND points to the camName metadata)
- Hit `https://www.youtube.com/@<channel>/streams` and search for the cam title

For Big Sky, that meant:
```
https://www.bigskyresort.com/.../webcams   → camstreamer embed URL
                    ↓
https://www.youtube.com/@BigSkyResort/streams   → live YT video IDs
```

---

## Files saved

| Path | Purpose |
|------|---------|
| `camera_testing\bigsky_cam.bat` | Double-click .bat for Big Sky live cams |
| `camera_testing\bigsky_webcams.html` | Saved page HTML of the Big Sky webcams page |
| `camera_testing\gautefall_webkamera.html` | Saved page HTML of the Gautefall cam page |
| `camera_testing\gautefall_mobotix.html` | (empty — Mobotix host unreachable) |
| `docs\BIGSKY_AND_GAUTEFALL_CAMS.md` | This file |