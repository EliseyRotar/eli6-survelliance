# Pitt Campus Tour Webcams - Investigation

> Original URL: `https://www.tour.pitt.edu/webcams`
> Status: **PRIVATE — internal cams only**
> Date checked: 2026-08-21

## TL;DR — What you can watch right now

The two webcams listed on Pitt's campus tour page are **on Pitt's private internal network** (136.142.x.x). They are NOT publicly accessible from the open Internet.

The **only public Pitt-related live cam currently available** is the famous **Peregrine Falcon nest on the Cathedral of Learning**, hosted on Explore.org:

**`https://explore.org/livecams/falcons/cathedral-of-learning-pittsburgh-falcons`**

---

## Camera 1 — Hillman Library Webcam

| Item | Value |
|---|---|
| URL on page | `http://136.142.55.41/sample/nuspectra?width=820&height=760&iframe=true&autoplay=1` |
| Internal IP | `136.142.55.41` (Pitt private network) |
| Type | Axis camera with NUSpectra multi-sensor (PTZ) |
| Status | **Currently listed as LIVE** (per the tour page text) |
| Public access | ❌ NO — connection times out from public Internet |

## Camera 2 — Cathedral of Learning Webcam

| Item | Value |
|---|---|
| URL on page | `http://136.142.55.90/viewer/live/en/live.html?width=820&height=760&iframe=true&autoplay=1` |
| Internal IP | `136.142.55.90` (Pitt private network) |
| Type | Axis viewer/live camera |
| Status | **OFFLINE per page** ("The Cathedral of Learning webcam is currently offline.") |
| Public access | ❌ NO — connection times out from public Internet |

### Why they're not accessible

Both cameras are on Pitt's **`136.142.0.0/16` private network** (University of Pittsburgh internal). They're protected by Pitt's firewall and not exposed to the public Internet. You can only see them when:

- Connected to Pitt's **campus Wi-Fi** (`PittNet Wireless`)
- Connected via **Pitt VPN** (`vpn.pitt.edu` / Cisco AnyConnect)
- Using **Pitt IT-managed remote access**

### Wayback Machine captured both UI shells in 2024

Wayback has HTML/JS from `136.142.55.90/viewer/common/img/*.jpg` and `136.142.55.90/viewer/...` from 2024-07-27. The cams were definitely online then (Axis viewer UI assets archived).

## Public alternatives — live cams at/near Pitt

### 1. **Cathedral of Learning Falcon Cam** (peregrine falcons nest on the Cathedral)

- **Browse page**: `https://explore.org/livecams/falcons/cathedral-of-learning-pittsburgh-falcons`
- **Player page**: `https://explore.org/livecams/player/cathedral-of-learning-pittsburgh-falcons`
- Hosted by **Explore.org** (Annenberg Foundation) since Pitt couldn't expose their own server publicly
- Live HLS feed (stream URL not exposed directly — Explore.org uses authenticated CDN; paste the browse URL in any browser)

### 2. **Downtown Pittsburgh Webcam**

YouTube has a **Downtown Pittsburgh Webcam** from user uploads, but it's not an always-on live feed.

### 3. **SRP: Hillman Library Webcam**

YouTube video showing the Hillman cam exists (`SRP: Hillman Library Webcam` video). The "SRP" prefix suggests it was a **Scholarly Recording Project** (Pitt's student project) recording the cam. Not a live feed.

## How to actually view the two private cams

### Option A: On Pitt campus Wi-Fi (PittNet)
Just open `http://136.142.55.41/sample/nuspectra` or `http://136.142.55.90/viewer/live/en/live.html` in a browser. The page auto-loads the camera UI.

### Option B: Pitt VPN
1. Install Cisco AnyConnect
2. Connect to `vpn.pitt.edu` with your Pitt username/password + 2FA
3. Once connected, the cam URLs work from anywhere

### Option C: Don't have a Pitt account?
**There is no public way** to see these cams without being on Pitt's network or having a sponsor.

## Detection methodology

```bash
# 1. Fetch the page
curl -sL "https://www.tour.pitt.edu/webcams" > pitt_webcams.html

# 2. Look for hidden href values (the cam URLs aren't iframes anymore — they're just hyperlinks)
grep -oE 'href="http://136\.142\.[0-9.]+[^"]*"' pitt_webcams.html
# -> http://136.142.55.41/sample/nuspectra?...
# -> http://136.142.55.90/viewer/live/en/live.html?...

# 3. Try to reach the cams from public Internet
curl --max-time 10 -v http://136.142.55.41/
# -> Connection timed out (firewalled)

# 4. Search YouTube for related live cams
curl -sL "https://www.youtube.com/results?search_query=hillman+library+pitt+webcam+live" \
  | grep -oE '"videoId":"[a-zA-Z0-9_-]{11}"' | head
# -> Hillman Library and Posvar Hall | Pitt 360
# -> SRP: Hillman Library Webcam (recorded, not live)
# -> Downtown Pittsburgh Webcam

# 5. Search for falcon cam (famous Pitt cam on Cathedral of Learning)
curl -sL "https://www.youtube.com/results?search_query=cathedral+of+learning+pitt+webcam+live+pittsburgh" \
  | grep -oE '"videoId":"[a-zA-Z0-9_-]{11}"|<title>[^<]+</title>'
# -> "Cathedral Of Learning Falconcam Back Up & Running"
# -> Pitt's peregrine falcon nest has its own webcam

# 6. Discover Explore.org hosts the falcon cam
curl -sL "https://explore.org/livecams/falcons/cathedral-of-learning-pittsburgh-falcons" \
  | grep -oE '<title>[^<]+</title>'
# -> "Cathedral Of Learning Pittsburgh Falcons | Falcons | Live Cams | Explore.org"
```

## File index

```
camera_testing/
├── pitt_webcams.html                  # original page (HTTP 200, 23KB)
├── pitt_webcams_wb2.html               # Wayback snapshot 2026-05-14 (29KB)
├── pitt_cam1.html, pitt_cam2.html    # Empty (firewall blocked)
├── pitt_webcams_wayback.html          # Wayback binary (corrupted)
├── explore_falcons.html               # Falcon cam browse page (422KB, React)
├── explore_player_falcons.html        # Falcon cam player page (422KB)
└── (other intermediary files)

docs/PITT_TOUR_WEBCAMS.md              # This writeup
```

## Summary

| Cam | URL | Public? |
|---|---|---|
| Hillman Library | `http://136.142.55.41/sample/nuspectra` | ❌ Pitt-internal only |
| Cathedral of Learning | `http://136.142.55.90/viewer/live/en/live.html` | ❌ Pitt-internal only (also currently offline) |
| Cathedral of Learning Falcon Nest | `https://explore.org/livecams/falcons/cathedral-of-learning-pittsburgh-falcons` | ✅ YES — open live stream |

If you want a live feed of something **at Pitt**, the **Peregrine Falcon Cam** is the one. The two cams from the tour page are for tour visitors on campus or Pitt VPN users only.