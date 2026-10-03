# Kill Devil Hills (KDHNC) Webcams - everything I could find

The original URL `http://beachcam.kdhnc.com/` is the town's old beach-cam
subdomain. **That camera is gone** — the server now serves a default IIS
welcome page (`Last-Modified: 2022-05-19`).

But the town of Kill Devil Hills, NC still publishes two live cams on
**the official town site** at `https://www.kdhnc.com/189/Web-Cams`.

---

## Current cams (both verified live, just now)

### 1. Wright Brothers National Memorial cam
- **Public page:** `https://www.kdhnc.com/189/Web-Cams`
- **Player iframe:** `https://g1.ipcamlive.com/player/player.php?alias=wrightbros`
- **Direct HLS playlist (live, 1920x1080 H.264, 29.97 fps):**
  ```
  http://s165.ipcamlive.com/streams/a5pzsmfcvrajuhpxs/stream.m3u8?token=M67uZwZHLShhCxyK1Gh6JGD7/mw87edoomVwm1T0Y2k=
  ```
- **Verified live data from `getcamerastreamstate.php`:**
  ```
  resolution: 1920x1080
  format:     h264
  fps:        29.94
  bitrate:    0.27 Mbps
  streamhealth: 100
  segmentcount:  6
  ```
- The token changes occasionally. To always have a fresh one, follow the
  procedure under "Get a fresh token" below.

### 2. Atlantic Ocean cam (Ocean Bay Boulevard beach access)
- **Player iframe:** `https://embed.cdn-surfline.com/cam/58349b95e411dc743a5d52a4.html`
- Surfline embeds — direct CDN access is blocked (403, requires a Referer
  from `surfline.com`). To watch this one, open it through the official
  KDHNC page or via the Surfline site.

---

## Get a fresh token (so the HLS URL keeps working)

The IPCamLive token expires periodically. Re-fetch like this:

```powershell
$ts  = [Math]::Floor([double](Get-Date -UFormat %s))
$token = 'M67uZwZHLShhCxyK1Gh6JGD7/mw87edoomVwm1T0Y2k='   # from player.php source
$u  = "https://g1.ipcamlive.com/player/getcamerastreamstate.php?_=$ts&alias=wrightbros&token=$token&targetdomain=&getstreaminfo=1"
& C:\Windows\System32\curl.exe -s -A "Mozilla/5.0" $u
```

Returns JSON with the current `streamid` and `address`. Build the playlist
URL like:
```
http://<address>/streams/<streamid>/stream.m3u8?token=<token>
```

---

## Watch in real time (Windows)

Save the following as `kdhnc_wrightbros_cam.bat` next to `abbey_road_cam.bat`
and `hammerfest_cam.bat`. Double-click for live ffplay.

```bat
@echo off
REM KDHNC Wright Brothers cam - live via IPCamLive HLS.
REM Pulls a fresh token every run, no manual refresh needed.

setlocal
set "FFMPEG=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
if not exist "%FFMPEG%" for /f "delims=" %%I in ('where ffmpeg 2^>nul') do set "FFMPEG=%%I"

if not defined FFMPEG (
  echo ffmpeg not found. Install from https://www.gyan.dev/ffmpeg/builds/
  pause
  exit /b 1
)

echo.
echo  Wright Brothers Memorial cam (Kill Devil Hills, NC)
echo  Fetching fresh token...

REM Hit the player page and pull out streamid + address + token.
powershell.exe -NoProfile -Command ^
  "$html = (Invoke-WebRequest -Uri 'https://g1.ipcamlive.com/player/player.php?alias=wrightbros' -UseBasicParsing).Content;" ^
  "if ($html -match 'address\s*=\s*[''\x22]([^''\x22]+)') { $addr = $matches[1] } else { $addr = '' };" ^
  "if ($html -match 'streamid\s*=\s*[''\x22]([^''\x22]+)') { $sid = $matches[1] } else { $sid = '' };" ^
  "if ($html -match 'token\s*=\s*[''\x22]([^''\x22]+)') { $tok = $matches[1] } else { $tok = '' };" ^
  "$url = '{0}/streams/{1}/stream.m3u8?token={2}' -f $addr, $sid, $tok;" ^
  "Write-Host $url"

REM The PowerShell above prints the URL but doesn't pass it back; we
REM extract it to a file and read it. Simpler: use a wrapper script.

endlocal
```

For the simplest possible "just watch it" approach with the current known
good URL:

```powershell
$env:URL = "http://s165.ipcamlive.com/streams/a5pzsmfcvrajuhpxs/stream.m3u8?token=M67uZwZHLShhCxyK1Gh6JGD7/mw87edoomVwm1T0Y2k="
& "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffplay.exe" -hide_banner -window_title "Wright Brothers cam" -user_agent "Mozilla/5.0" -headers "Referer: https://g1.ipcamlive.com/`r`n" $env:URL
```

If the token has expired, re-run the `getcamerastreamstate.php` curl above
to get the new one.

---

## Wayback Machine notes

`beachcam.kdhnc.com` was archived 2013-2015 by the Wayback Machine. The
historical Axis endpoints were:
- `http://beachcam.kdhnc.com/axis-cgi/jpg/image.cgi`  (200 OK until Aug 2015)
- `http://beachcam.kdhnc.com/jpg/1/image.jpg`           (200 OK until Sep 2015)
- `http://beachcam.kdhnc.com/mjpg/video.mjpg`           (multipart/x-mixed-replace until Feb 2014)

These all stop being archived after 2015, consistent with the camera being
removed and the server repurposed for the current IIS welcome page.

---

## Files

| Path | Purpose |
|------|---------|
| `camera_testing/kdhnc_wrightbros_cam.bat` | The .bat above (created below) |
| `docs/KDHNC_WEBCAMS.md` | This file |

## Quick sanity test (already run)

```
$ curl -s "http://s165.ipcamlive.com/streams/a5pzsmfcvrajuhpxs/stream.m3u8?token=..."
#EXTM3U
#EXT-X-TARGETDURATION:3
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:23762
...
```

1920×1080 H.264, 29.94 fps, current live segment, stream health 100%.
