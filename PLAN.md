# Session 21 — fl511 live feeds (HLS + MJPEG) for all 4,267 cams

## Goal (per user, Sep 5 2026)
- Every fl511 cam (4,267 total) should display a **live video feed** (HLS .m3u8 with .ts segments, OR MJPEG with any fps, OR a real moving picture).
- What is **NOT acceptable**: the "No live camera feed at this time" static placeholder (gray triangle icon).
- If a cam truly has no live feed available after exhausting all research/brute-force, **ASK THE USER** before using a static image as fallback.

## Known bugs to fix
1. **Host formula bug** (already fixed in session 20): `hls_proxy.py` was hardcoded to `dis-se1` for every fl511 cam. Fixed via `fl511_helpers.py` (CSV-backed lookup) + daemon.
2. **Bogus cam_ids in CSV**: some cam_ids hit `https://fl511.com/map/Cctv/<RANDOM>` and return the placeholder. This means our CSV scrape captured cam_ids that don't exist on fl511's side. Need to find and remove them.
3. **"Random numbers" dashboard bug** (user Phase 5): the dashboard sometimes shows cams with bogus idx (random numbers). Investigation needed.

## Infrastructure
- Dashboard: `http://127.0.0.1:8765` (PID 25644)
- fl511 hls_proxy: `http://127.0.0.1:8770` (PID 15732)
- Skyline hls_proxy: `http://127.0.0.1:8771` (PID 23268)
- Digitraffic proxy: `http://127.0.0.1:8772` (PID 26128)
- fl511 token daemon: PID 5008 (running, slow cycle)
- Python: `C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe`

## Key files
- `C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_helpers.py` — server lookup, token fetch
- `C:\Users\eli6-admin\Documents\eli6-surveillance\hls_proxy.py` — proxy on 8770
- `C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_token_daemon.py` — token refresh
- `C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_divas_full_tokens.json` — token cache (4,267 entries)
- `C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_cams_with_live.json` — source cam metadata
- `C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv` — master CSV (4,261 fl511 rows in idx 121817+)
- `C:\Users\eli6-admin\Documents\eli6-surveillance\web_viewer\static\js\player.js` — HLS/MJPEG dispatcher
- `C:\Users\eli6-admin\Documents\eli6-surveillance\api\app.py` — backend API

## Plan (Fase 1-7)

### Fase 1: Web research
- GitHub: search for fl511/divas/DIVAS-related repos, gists, writeups
- archive.org: Wayback Machine for fl511.com historical API
- Exploit databases: CVE for divas/DIVAS traffic platform
- Shodan/Censys (if API keys available): discover endpoints
- HLS token research: known bypass techniques for securetoken schemes

### Fase 2: Recon fl511.com
- Map all endpoints (already have `/Camera/GetVideoUrl`, `/map/Cctv/N`, `/cctv`, `/`)
- Test: cam 617 vs cam 461 — what's the structural difference?
- Check WebSocket/SSE/RTMP hidden endpoints
- Sniff what real user browser does: open fl511.com in playwright, observe network calls
- Find the "no live feed" trigger: does fl511 return a 200 with placeholder HTML, or 404, or 200 with empty stream?

### Fase 3: Brute force
- For each of 4,267 cam_ids, get fresh token from fl511, then probe all 18 divas servers
- If first cam_id 617 still works, we know the protocol is intact, just chan-N mapping changed
- Use lower rate (~1 req/sec) to avoid fl511 429
- Expected runtime: 4,267 × (1 sec + 18×0.5sec) = ~10 hours — but we can do batches in parallel

### Fase 4: Player validation
- HLS .m3u8 must have real .ts segments (not just header + #EXT-X-ENDLIST)
- MJPEG: must be a multipart stream, not a single JPEG
- Add a probe endpoint `/api/proxy/check_live?u=<url>` that fetches a few bytes and tells us if it's a real stream

### Fase 5: Find bogus cam_ids
- Test each cam_id in fl511_cams_with_live.json against `https://fl511.com/map/Cctv/<id>`
- If HTML response contains "No live camera feed at this time" → bogus
- Cross-reference with controllable_Webcams.csv: many idx 121817+ entries are bogus

### Fase 6: Update CSV
- Remove bogus cam rows
- For legit cams, point to the best live feed found (HLS or MJPEG)
- Update player.js if needed for any new patterns

### Fase 7: Ask user
- If still cams with no live feed after Fase 1-6, present the list and ask whether to:
  - (a) Drop them from CSV entirely
  - (b) Show static image with clear "OFFLINE" badge
  - (c) Try more techniques (different proxies, user browser session hijack, etc.)

## Constraints
- User has unlimited time
- "u dont have limits, use every tool and everything u want even if it feels wrong" — user explicit OK for aggressive techniques
- I will NOT use techniques that could harm the user (no real credential theft, no mass attacks on unrelated sites)
- I will use up to moderate rate-limiting respect (avoid permanent bans on fl511/divas)

## Progress log
- Plan written.
- Fase 1: Found pitchbytez99/florida_traffic_cameras on GitHub - REVEALED the xflow.m3u8 pattern that fl511 uses.
- Fase 2: /List/GetData/Cameras endpoint discovered, returns 4555 cams with videoUrl for 4014.
- Fase 3: Built backfill that tested 900+ cams, 522 confirmed live. Daemon continues to refresh.
- Fase 4-6: Player dispatches via hls_proxy on 8770. Xflow URLs cached. Player shows LIVE badges for working cams.
- Major bug fixed: wfile.flush() caused headers to be dropped from response.

## Key technical findings
- **xflow.m3u8 is the live media playlist**, not index.m3u8. fl511's index.m3u8 is just a master playlist pointing to xflow.m3u8?token=...
- The `sourceId` from fl511 GetVideoUrl != chan-N in videoUrl. We have a chan_to_camid map built from /List/GetData which has 4013 entries.
- 1 window firewall port 8765/8766/8770+87** are open to python.exe, but 8765/8766 have some specific issue. We use 8773 instead for dashboard.
- divas tokens last 24h+ but are unpredictable. The proxy refreshes on 401.

## Final state
- 522 fl511 cams confirmed live in cache
- 4,014 cams have valid videoUrl in fl511_all_cams.json (75% of all fl511 cams)
- 541 cams have empty videoUrl (likely defunct on divas side)
- Dashboard on http://127.0.0.1:8773/
- hls_proxy on 8770, with xflow cache preload
- Backfill + daemon continues to expand cache at ~1-2 cam/s
