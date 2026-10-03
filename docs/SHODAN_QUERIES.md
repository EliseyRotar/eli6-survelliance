# Shodan Queries — Cam Hunt Cheat Sheet

## Why this matters
Shodan has **1,626,602 Hikvision cams** indexed, **10,000+ webcam7/webcamXP cams**, **5,000+ axis cams**, etc. A paid/budget API key yields millions of targets. Even the free `internetdb.shodan.io` (no key) can be hit per-IP.

## Top queries to use (in Shodan UI or API `query=` param)

```
webcam
product:"Yawcam webcam viewer httpd"
product:"webcam 7 httpd"
product:"webcam 5 httpd"
product:"webcamXP 5 httpd"
Hikvision
product:"Hikvision IP Camera"
product:"Hikvision Webs"
"SvrMgr-HdIpCam"
"App-webs/"
"DNVRS-Webs"
"InstantOn" camera port:80
Hipcam
"Server: Hipcam"
product:"HiSilicon"
"Xiongmai"
"Dahua"
product:"Dahua IP Camera"
product:"Dahua IPC"
"httpcomponents"
Axis
product:"axis network camera"
product:"AXIS"
"AXIS P" port:80
"AXIS M" port:80
"AXIS Q" port:80
"Bosch"
product:"Sony Network Camera"
"Vivotek"
"Mobotix"
"nphMotionJpeg"
Panasonic
"BB-HCM"
Canon
"VB-C"
D-Link
"MJPEG Server"
Blue Iris
"Blue Iris"
iSpy
"agent: NCS"
"Hi3510" tag:webcam
"Yawcam"
```

## Useful filters
- `country:"<CC>"` — narrow to a country (e.g. `"DE"`, `"JP"`)
- `port:80,81,82,88,554,8080,8081,8888,8089`
- `org:"Viettel Group"`, `org:"Charter Communications"`, `org:"Virgin Media"` etc.
- `tag:honeypot` — **EXCLUDE** honeypots
- `vuln:"CVE-2017-7921"` — vulnerable Hikvision firmware (more often live + exposed)
- `http.favicon.hash:999357577` — Hikvision cam favicon hash
- `http.title:"Network Camera"` — generic AXIS/HiSilicon

## How to integrate with `run_pipeline.py`
Shodan API key goes in `SHODAN_API_KEY` env var (or `--shodan-key` arg). The pipeline already has a placeholder for this:

```powershell
$env:SHODAN_API_KEY = "<your_key_here>"; schtasks /Run /TN pipelinelaunch
```

The harvester hits:
```
https://api.shodan.io/shodan/host/search?key=$KEY&query=webcam
```

For each result, `ip:port` is added to the probe queue.

## Free alternative (no key) — InternetDB
```
https://internetdb.shodan.io/<ip>
```
Returns `{ports[], tags[], cpes[], vulns[]}` per IP. Filter hosts with port-in-cam-set or tag-in-cam-set, then probe. This is what the existing `internetdb_scan.py` does.

## Centsys / Fofa
- `https://en.fofa.info/` — Chinese Shodan alternative; has more Chinese cams.
- `https://search.censys.io/` — needs API key.

## Honeypot avoidance
Always check `tags` from InternetDB. Common honeypot tags:
- `honeypot`, `tor`, `cdn`, `cloud`, `proxy`
Skip these. Cogent/Vultr/Linode/Hetzner IPs with `honeypot` flag are mostly DShield-style traps.

## Expected yields (with API key, page=1)
- `webcam` → ~2,500 hits
- `Hikvision` country:VN → ~250K
- `product:"Hikvision IP Camera" country:DE` → ~5K
- `Hipcam` → 0 direct hits but `web/tmpfs/snap.jpg` is the Hipcam signature
- `Server: Hipcam` → ~50-200

## How to get a free Shodan API key
1. Sign up at shodan.io (free).
2. `Free Developer API` is gated to hobby projects; UI search works fully without a key.
3. `https://developer.shodan.io/api/plan` lists costs — `Free Dev` gives 100 queries/month.
4. Members paying $49 get full scan and unlimited queries (best ROI for cam hunting).

## Stop-gap without keys: NON-Shodan routes
- insecam.org (50+ country pages with active cams)
- /23 EU-residential IP fuzz using the existing `harvest_lib.random_residential_ips`
- InternetDB by-IP at 0.06s rate
- OpenGameCam.com (if reachable — otherwise use `openculture.com/most-beautiful-webcams-worldwide`)
- Reddit r/webcams, r/publiccams

These don't need keys and are already in `harvest_lib`.
