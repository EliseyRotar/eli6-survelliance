# Abbey Road Crossing Cam — how to actually watch it

The live stream is hosted by **EarthCam**, which **hotlink-blocks** bare GET
requests. The page `https://www.abbeyroad.com/crossing` works because the
embedded player sends the right `Referer` and `Origin` headers. When you
point VLC directly at the stream, you get `403 Forbidden`.

This doc covers three ways to actually watch it.

---

## 1. Easiest — open it in a browser

Just go to:

```
https://www.abbeyroad.com/crossing
```

Click the **LIVE** button. The page uses `video.js` with HLS and serves
the stream itself. Works in Chrome, Firefox, Edge, Safari.

---

## 2. Watch in VLC (recommended)

VLC doesn't honour custom headers when you paste the URL into its GUI,
but it does honour them on the **command line** with `--http-referrer`
and `--http-user-agent`.

### Get the playlist first (sanity check)

```powershell
curl.exe -I `
  -H "Referer: https://www.abbeyroad.com/crossing" `
  -H "Origin:   https://www.abbeyroad.com" `
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36" `
  "https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/playlist.m3u8"
# Expect: HTTP/1.1 200 OK
#         Content-Type: application/vnd.apple.mpegurl
```

### Watch with VLC (Windows, PowerShell)

```powershell
$vlc = "C:\Program Files\VideoLAN\VLC\vlc.exe"     # adjust if needed
& $vlc `
  --http-referrer="https://www.abbeyroad.com/crossing" `
  --http-user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36" `
  --http-origin="https://www.abbeyroad.com" `
  "https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/playlist.m3u8"
```

On Linux/macOS:

```bash
vlc \
  --http-referrer='https://www.abbeyroad.com/crossing' \
  --http-user-agent='Mozilla/5.0 ...' \
  --http-origin='https://www.abbeyroad.com' \
  "https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/playlist.m3u8"
```

The flags are `--http-referrer`, `--http-user-agent`, `--http-origin`
(singular `referrer`, not `referer` — VLC is picky about the spelling).

---

## 3. Save a clip with ffmpeg (works, tested here)

```powershell
ffmpeg.exe `
  -hide_banner -loglevel error `
  -user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36" `
  -headers "Referer: https://www.abbeyroad.com/crossing`r`nOrigin: https://www.abbeyroad.com`r`n`r`n" `
  -i "https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/playlist.m3u8" `
  -t 10 -c copy "C:\path\to\abbeyroad_clip.mp4"
```

> In PowerShell, `` `r`n `` is how you embed a literal CR+LF inside the
> ` -headers` block. The trailing empty line is required by the HTTP spec.

Verified locally: 10-second clip ≈ 1 MB, 1920×1080 H.264 + AAC.

---

## What's actually flowing

The HLS playlist points to:

```
#EXT-X-VERSION:4
#EXT-X-STREAM-INF:BANDWIDTH=970362,CODECS="avc1.64002a,mp4a.40.2",RESOLUTION=1920x1080
chunklist_w717469888.m3u8
```

So it's **1920×1080, ~970 kbps, H.264 + AAC** — a single quality variant.
Live chunks are fetched from the same EarthCam CDN with the same
hotlink check.

The original `controllable_Webcams.csv` entry `http://www.abbeyroad.com/crossing`
now resolves to the same cam — it just looks like a regular web page to
`check_ip_availability.py`, not a video stream.

---

## Other endpoints (verified)

| URL | Status |
|-----|--------|
| `https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/playlist.m3u8` | 200 OK (with headers) |
| `rtmp://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv` | RTMP fallback (Flash/old players) |
| `https://static.earthcam.com/hof/england/abbeyroad/external/med/17872575506655_61_med.jpg` | 206, image/jpeg (Wall-of-Fame thumbnail) |
| `https://www.abbeyroad.com/crossing` | 200 OK (the player page) |

EarthCam archive JSONP endpoint (for the Wall of Fame):
`https://www.earthcam.com/scripts/net/get_archive_data.php?netid=640258597cbc50037072712f964cf5d8`
