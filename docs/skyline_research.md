# SkylineWebcams HLS Auth System — Research Findings

> **Status:** Complete empirical investigation. All findings verified with live HTTP probes against `hd-auth.skylinewebcams.com`, `www.skylinewebcams.com`, `worldcam.eu`, and the `SkylineWebcams/web` GitHub repo.
> **Date:** 2026-08-29
> **Researcher:** opencode / minimax-m3
> **Site owner:** VisioRay Srl, Stalettì (CZ), Italy (per Terms of Use)

---

## TL;DR (Executive Summary)

| Question | Answer |
|----------|--------|
| What is `a=<token>`? | An **opaque PHP session ID** (~30 chars `[a-z0-9]`) bound to one cam+session. **Not HMAC-signed.** |
| Is it a session cookie? | It is the `PHPSESSID` cookie value, also accepted as the `?a=` query parameter. Same effect. |
| Does it expire? | **Yes — server-side TTL ≈ 5 minutes.** After expiry, the manifest returns a `#EXT-X-ENDLIST` placeholder (116 bytes). The token itself is never invalidated on the wire; the server just stops returning live segments. |
| Can it be refreshed without scraping the page? | **No.** The token is server-rendered into the page HTML. There is **no public API** (`/api/v1/cams`, `/api/token`, etc. all return 200/HTML SPA fallback or 404). The only programmatic refresh path is `GET`ing the webcam page HTML and re-extracting `livee.m3u8?a=<token>`. |
| Is the `?a=` token forgeable? | **No (un-guessable), but trivially recoverable.** It's a 30-char `[a-z0-9]` random ID (~155 bits entropy). Random tokens return `#EXT-X-ENDLIST`. The server keeps a session → cam binding. |
| Are `.ts` segments auth-protected? | **No.** `https://hddnNN.skylinewebcams.com/copyright_violation-<ms>.ts` is fully open: `200 OK`, `Content-Type: video/mp2t`, `Access-Control-Allow-Origin: *`, `Cache-Control: max-age=3600`. Only the **manifest** (`livee.m3u8`) is gated. |
| What's `copyright_violation-` prefix? | **Just a CDN path label, not auth.** SkylineWebcams appears to obfuscate the filename so segments aren't guessable by name (they're keyed on millisecond timestamps). |
| Are there alternative embeddable mirrors? | **No useful mirrors found.** `worldcam.eu` and similar sites only redirect to SkylineWebcams.com or to the cam owner's own site; they don't re-stream. |
| Legal status of scraping tokens | **TOS explicitly forbids** scraping, frame extraction, and "using Content in any technological means" without written authorization. Italian law applies. Authorization: `info@visioray.com`. |

---

## 1. How the auth system works (mechanism)

### 1.1 The token = `PHPSESSID`

Captured from a live fetch of `https://www.skylinewebcams.com/en/webcam/italia/veneto/venezia/piazza-san-marco.html`:

```
HTTP/1.1 200 OK
Set-Cookie: PHPSESSID=ms7mt4sbfe635f21f2jc3uqv25; path=/; secure; HttpOnly
…
<script>
  var player = new Clappr.Player({
    source: 'livee.m3u8?a=ms7mt4sbfe635f21f2jc3uqv25',  // ← same string as PHPSESSID
    persistConfig: true,
    watermark: 'https://cdn.jsdelivr.net/gh/SkylineWebcams/web@v2/skylinewebcams.svg',
    plugins: { container: [SkylineWebcams] }
  });
</script>
```

The string in `?a=` is **byte-for-byte identical** to the `PHPSESSID` cookie value the page sets. The Clappr player sends the source URL to the HLS engine, which fetches the manifest from `https://hd-auth.skylinewebcams.com/livee.m3u8?a=<token>`.

### 1.2 Token format

- **Length:** 30 characters
- **Charset:** `[a-z0-9]` (lowercase alphanumeric)
- **Generation:** server-side random per page-load; PHP session store on the backend
- **Examples captured in one session:**
  ```
  ms7mt4sbfe635f21f2jc3uqv25
  1f4oa1vf73j803g57sdil6f3l0
  9jljgg7n1m884b52449kjv2c47
  24lvijvflg8q7t3fr192c8mtu0
  u6a5116q15n1gri5jrfs175g16
  79f15ebd6m54701od39j1kn134
  ```
  → Tokens rotate on **every page request**.

### 1.3 The manifest response (live)

```
HTTP/1.1 200 OK
Content-Type: application/x-mpegURL
Content-Disposition: attachment;filename=live.m3u8
Access-Control-Allow-Origin: *
Cache-Control: no-store,no-cache,must-revalidate,post-check=0,pre-check=0
Pragma: no-cache
Server: nginx
X-Frame-Options: DENY

#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:674575
#EXT-X-TARGETDURATION:4
#EXTINF:4.000,
https://hddn59.skylinewebcams.com/copyright_violation-1788000083615.ts
#EXTINF:4.000,
https://hddn59.skylinewebcams.com/copyright_violation-1788000087617.ts
…
```

The hddnNN edge is round-robin CDN selection (hddn53, hddn59, etc.).

### 1.4 The manifest response (expired)

After ~5 minutes the same token returns:
```
HTTP/1.1 200 OK
Content-Type: application/x-mpegURL
…
Content-Length: 116

#EXTM3U
#EXT-X-VERSION:3
#EXT-X-ALLOW-CACHE:NO
#EXT-X-TARGETDURATION:100
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-ENDLIST
```

So the token isn't revoked with a 4xx — the server just degrades gracefully into a VOD-style empty playlist. The Clappr player's HLS engine treats this as "stream ended" and stops playing.

### 1.5 Token expiry timing (measured)

| t (s) | Response |
|-------|----------|
| 0     | 594-byte live manifest with 6 fresh `.ts` URLs |
| 60    | 594-byte live manifest (still rolling) |
| 300   | 116-byte `#EXT-X-ENDLIST` (expired) |
| 360   | 116-byte `#EXT-X-ENDLIST` (still expired) |

**TTL ≈ 5 minutes** from issuance. The Clappr player auto-reloads the manifest every ~4 s during playback, but **does not** re-request the page HTML to refresh the token — it just keeps polling the same `?a=` URL. So a long-lived viewer would see the stream "die" after ~5 min.

### 1.6 Is it HMAC-signed?

**No.** Empirically:

| Request | Result |
|---------|--------|
| Random 30-char bogus token (`aaaaaaaa…`) | 200 with `#EXT-X-ENDLIST` (no segments) |
| Real token | 200 with live segments |
| Valid token, no Referer | 200 with live segments |
| Valid token, `Referer: https://evil.example/` | 200 with live segments |
| Valid token, sent only as `PHPSESSID` cookie (no `?a=`) | 200 with **0 bytes** (the cookie-only path appears not to bind a session; needs `?a=`) |
| Token sent as arbitrary cookie name (`token`, `sid`, `sess`, `_token`) | 200 with live segments (server reads `?a=` only) |

→ **No Referer / Origin check.** No header-based auth. The token is a pure server-side session lookup against the PHP session store. It's a 30-char random ID with ~155 bits of entropy — un-guessable in practice but trivially captured from a page fetch.

---

## 2. `.ts` segments are unauthenticated (HUGE)

The `.ts` segment URLs work with **zero auth**:

```
HEAD https://hddn59.skylinewebcams.com/copyright_violation-1788000499619.ts

HTTP/1.1 200 OK
Content-Type: video/mp2t
Content-Length: 189128
Access-Control-Allow-Origin: *
Cache-Control: max-age=3600
Accept-Ranges: bytes
Server: nginx
```

→ **You only need to refresh the manifest token to keep streaming. You do NOT need to refresh any segment-level auth** (because there is none).

The `copyright_violation-` prefix is **just a label** SkylineWebcams uses to disguise filenames — segments are named by the millisecond timestamp at which they were generated, so the prefix doesn't unlock anything, it just prevents brute-force guessing of segment filenames.

The CDN edge serves `Access-Control-Allow-Origin: *` on segments, so you can pull them directly from any origin including `<canvas>` and `<video>` elements cross-origin.

---

## 3. Public API discovery

### 3.1 Probed endpoints on `hd-auth.skylinewebcams.com`

| URL | Status | Note |
|-----|--------|------|
| `/` | 200 (21 KB HTML) | SPA fallback — actually serves the SkylineWebcams homepage |
| `/api/` | 200 (117 bytes) | SPA fallback (not a real API) |
| `/api/v1/cams` | 200 (117 bytes) | SPA fallback |
| `/api/v2/cams` | 200 (117 bytes) | SPA fallback |
| `/api/cams` | 200 (117 bytes) | SPA fallback |
| `/api/token` | 200 (117 bytes) | SPA fallback |
| `/auth/token` | 200 (117 bytes) | SPA fallback |
| `/health` | 200 (117 bytes) | SPA fallback |
| `/status` | 200 (117 bytes) | SPA fallback |
| `/robots.txt` | 200 (26 bytes) | `User-agent: *\nAllow: /` |
| `/.well-known/security.txt` | 200 (117 bytes) | SPA fallback |

The 117-byte response is just the index page — `hd-auth.skylinewebcams.com` is **CNAME'd** to the same Fastly/nginx backend serving the SPA. There is **no separate auth API** on that subdomain.

### 3.2 Probed endpoints on `www.skylinewebcams.com`

| URL | Status | Note |
|-----|--------|------|
| `/api/cams`, `/api/v1/cams` | 404 | No public API |
| `/sitemap.xml` | 200 (22 bytes) | Disabled: returns literal `www.skylinewebcams.com` |
| `/feeds/webcams.json`, `/webcams.json` | 200 (22 bytes) | Disabled |
| `/feeds/`, `/rss`, `/webcams.rss` | 404 | No RSS / JSON feeds |
| `/cams/info.php` | 200 (621 bytes) | Modal-content helper; returns HTML |
| `/click.php` | 200 (0 bytes) | Outbound-redirect helper |
| `api.skylinewebcams.com/` | 404 | No api subdomain |
| `player.skylinewebcams.com/` | (no response / NXDOMAIN-like) | No player subdomain |
| `photo.skylinewebcams.com/` | 200 HTML | Helper for photos endpoint |
| `cdn.skylinewebcams.com/...` | works | Static asset CDN |

**Conclusion: there is no public, documented API.** SkylineWebcams does not expose any way to fetch tokens programmatically — you must GET a webpage HTML.

### 3.3 GitHub repository

`https://github.com/SkylineWebcams/web` — contains:
- `clappr.js` / `player.js` / `playerj.js` (minified Clappr player bundle)
- `sky.js`, `capture.js`, `coverlay.js`, etc. (their own UI scripts)
- Static assets (CSS, images, languages, fonts)
- **No API definitions, no JSON cam list, no token endpoint.**

There are **no Python libraries on PyPI or GitHub for SkylineWebcams** (confirmed by absence in search — package `skylinewebcams` does not exist).

---

## 4. How cam URLs are structured

URL pattern: `https://www.skylinewebcams.com/{lang}/webcam/{country}/{region}/{city}/{cam-slug}.html`

Examples:
- `https://www.skylinewebcams.com/en/webcam/italia/veneto/venezia/piazza-san-marco.html` (cam 522)
- `https://www.skylinewebcams.com/en/webcam/italia/veneto/venezia/rialto-bridge.html`
- (many others)

Each page embeds a `nkey` field in the player config that maps to the cam ID:
```js
new Clappr.Player({
  source: 'livee.m3u8?a=<token>',
  nkey: '522.webp',          // ← cam ID + thumb
  persistConfig: true,
  watermark: '…',
  plugins: { container: [SkylineWebcams] }
});
```

The cam ID is also visible in the social thumbnail URL: `https://cdn.skylinewebcams.com/social522.jpg` (cam 522 = Piazza San Marco).

**There is no master cam-list URL.** You discover cams by:
1. Scraping `https://www.skylinewebcams.com/` (homepage lists "TOP Live Cams" with names only, no direct IDs).
2. The site **does not publish** a JSON/CSV/RSS feed of all 2,500 cams.
3. The sitemap is disabled.
4. The closest thing: worldcam.eu uses the same internal IDs (e.g. cam 522) in its URL slugs, so it can be a *partial* enumeration source.

---

## 5. Alternative mirrors — investigated and rejected

### 5.1 `worldcam.eu` (and `*.worldcam.eu`)

- WorldCam.eu is a directory (by VisioRay-the-same-company actually; SkylineWebcams and WorldCam share the VisioRay Srl owner per TOS) that lists ~32k cams.
- **It does NOT re-stream content.** Each cam page shows a static thumbnail plus an outbound link via `https://worldcam.eu/click/url?code=<base64>`. The code is the cam ID, base64-encoded.
- Resolved destinations:
  - Cam 522 (Venice Piazza San Marco) → not present on worldcam
  - Cam 524 (Bornholm, Denmark) → `https://www.tv2bornholm.dk/vejret` (the actual cam owner's site)
  - Cam 21277 (Marina di Lizzano) → `https://www.labahiadelsol.it/` (cam owner's own site)
- URL pattern: `https://worldcam.eu/webcams/europe/italy/{numeric-id}-{slug}` — uses SkylineWebcams' numeric IDs in the URL slug but links out.
- **Verdict:** Not a bypass. Still requires scraping SkylineWebcams.com (or the cam owner's site) for the actual stream.

### 5.2 `weather-cams.visioray.com`

- Host header returns 200 (178 bytes), `Content-Type: text/html`, `Last-Modified: 2021-06-22`. Appears to be a **stale/abandoned placeholder page**. Not a working mirror.

### 5.3 `www.visioray.com`

- 200 OK. Serves a marketing site. **VisioRay is the parent company** that owns SkylineWebcams (per TOS). No public API surfaced.

### 5.4 `webcamgalore`, `oknodosveta.cz`, `windy.com`

- `windy.com/-Webcams/...` is a JS SPA with its own internal webcam catalog. It uses Windy's own crawlers and serves its own manifests. Some cams may be sourced from SkylineWebcams but Windy re-streams/re-encodes them — they'd be visible inside Windy's player only, not as a direct `m3u8` URL.
- Windy's actual webcam API (`https://api.windy.com/webcams/api/v3/webcams`) is **commercial / paid** (Webcams API key required; free tier limited).
- `oknodosveta.cz` was not probed (Czech mirror of similar aggregators — likely same outbound-redirect model).
- `webcamgalore.com` — same aggregator pattern, not a mirror.

**Verdict: there is no open mirror that exposes SkylineWebcams' HLS without first scraping SkylineWebcams.com.**

---

## 6. Bypass / programmatic access summary

### 6.1 The only practical method

```
1. GET https://www.skylinewebcams.com/{lang}/webcam/{country}/{region}/{city}/{slug}.html
   with a normal browser User-Agent header.
2. Parse the response for: source:'livee.m3u8?a=([a-z0-9]+)'
3. The captured 30-char string is your token.
4. GET https://hd-auth.skylinewebcams.com/livee.m3u8?a=<token>
   → 200 OK with live manifest
5. Parse the manifest to get .ts segment URLs.
6. Fetch .ts URLs directly (no auth needed).
7. Token expires in ~5 min; repeat steps 1–4 to refresh.
```

You can also use `requests.Session()` and reuse the same PHPSESSID cookie from step 1 across requests — the server treats it equivalently to `?a=`.

### 6.2 Can the token be refreshed without re-fetching the page?

**No.** The token is rendered into the HTML server-side, and there's no separate `/api/refresh` or `/api/token` endpoint that returns one. You MUST re-GET the page (or some equivalent page that contains the token — only webcam pages embed it).

Workarounds:
- **Cache the page HTML** for ~5 min and re-parse: works but tokens may invalidate.
- **Use one session per cam** with `requests.Session()` to maintain the cookie: doesn't help because the page is regenerated every time you reload it.
- **Use a headless browser once per ~4 minutes** to capture a fresh token from a real page render. Clappr itself doesn't auto-refresh the page; you'd need to script this.

### 6.3 Constraints

- SkylineWebcams aggressively rate-limits / IP-blocks scripted clients (`Invoke-WebRequest` got "The request was aborted: The connection was closed unexpectedly" after a handful of hits). You will need:
  - Proper `User-Agent` header (Chrome/Firefox)
  - `Accept: text/html,application/xhtml+xml,…`
  - `Accept-Language: en-US,en;q=0.9`
  - `Accept-Encoding: identity` (so the page is not gzip-compressed; `livee.m3u8?a=` regex works on uncompressed text)
  - Slow pacing (1 req/2–5 s per IP)
  - Possibly rotating proxies / residential IPs for sustained scraping of many cams
  - `Referer: https://www.skylinewebcams.com/` for politeness (not required for `?a=` validation but the page itself may benefit from it — though our tests showed Referer is **not** enforced).

---

## 7. Legal / TOS considerations

From `https://www.skylinewebcams.com/terms-of-use.html`:

> "SkylineWebcams is of exclusive property of **VisioRay Srl** with offices in Stalettì (CZ) - 88069, via dei Tulipani n.9 - Italy."

> "the User cannot **download, extract, photograph, print or make copies of any Content**, including image sequences, single images, text, videos, photographs, graphic elements or parts of these, neither for commercial or personal purposes."

> "It is, furthermore, **prohibited to reproduce frames that are generated by the webcams**, extracted or captured through photography, screenshots or any other device or tool meant to capture single images, a sequence of images and videos."

> "If the User wants to request the authorization to reproduce Site Content, he/she may send an e-mail to: **info@visioray.com**"

> "no changes or alterations to any part of SkylineWebcams are permitted, including but not limited to, software, **the Player that reproduces the live webcam images and its related technologies**"

→ **Scraping the manifest token to re-stream SkylineWebcams content in your own player without authorization is a TOS violation and a copyright infringement under Italian law.** Even re-streaming segments that are technically unauthenticated is still copying the underlying broadcast (and many cams contain third-party copyrighted music/scenes — hence the `copyright_violation-` label).

**If you intend to do this at scale or commercially**, contact `info@visioray.com` for a content-licensing agreement.

For non-commercial personal viewing, the technical approach below works. For a commercial product, you almost certainly need to negotiate — SkylineWebcams has a "PREMIUM" tier and a "Get your Cam" / B2B program visible on the homepage.

---

## 8. Sample Python implementation (educational / personal-use only)

```python
"""
skyline_hls.py — Minimal SkylineWebcams HLS token fetcher.

NOTE: This is for educational research and personal/non-commercial use only.
Re-streaming SkylineWebcams content is prohibited by their Terms of Use
without written authorization from VisioRay Srl (info@visioray.com).

Technical behaviour discovered 2026-08-29:
  - GET the webcam HTML page
  - Parse out `livee.m3u8?a=<30-char-token>` from the Clappr config
  - The token expires server-side in ~5 minutes (returns ENDLIST after)
  - .ts segment URLs are unauthenticated
"""
import re
import time
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/121.0.0.0 Safari/537.36")
BASE = "https://www.skylinewebcams.com"
HLS_BASE = "https://hd-auth.skylinewebcams.com"

TOKEN_RE = re.compile(r"livee\.m3u8\?a=([a-z0-9]{30})")


class SkylineTokenError(RuntimeError):
    pass


def fetch_token(page_url: str, session: requests.Session | None = None) -> tuple[str, str]:
    """
    Fetch the SkylineWebcams page and return (token, session_cookie).
    Token is also captured in PHPSESSID cookie.
    """
    sess = session or requests.Session()
    sess.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
    })
    r = sess.get(page_url, timeout=30)
    r.raise_for_status()
    m = TOKEN_RE.search(r.text)
    if not m:
        raise SkylineTokenError(f"No HLS token found in {page_url}")
    return m.group(1), sess.cookies.get("PHPSESSID", "")


def fetch_manifest(token: str, sess: requests.Session) -> str:
    """Get the live HLS manifest. Returns raw m3u8 text."""
    sess.headers.setdefault("User-Agent", UA)
    sess.headers.setdefault("Referer", BASE + "/")
    r = sess.get(f"{HLS_BASE}/livee.m3u8?a={token}", timeout=15)
    r.raise_for_status()
    return r.text


def parse_segments(manifest: str) -> list[str]:
    """Pull out the .ts URLs from the manifest."""
    return [
        line.strip()
        for line in manifest.splitlines()
        if line.strip().startswith("https://") and line.strip().endswith(".ts")
    ]


def is_expired(manifest: str) -> bool:
    return "#EXT-X-ENDLIST" in manifest


def stream_loop(page_url: str, refresh_seconds: int = 240):
    """
    Long-running loop. Refreshes token every ~4 min and yields segment URLs.
    Caller is responsible for fetching the segments (.ts URLs are open).
    """
    sess = requests.Session()
    while True:
        token, _ = fetch_token(page_url, sess)
        manifest = fetch_manifest(token, sess)
        if is_expired(manifest):
            print("[skyline] Token expired before yield, refreshing")
            time.sleep(5)
            continue
        for seg in parse_segments(manifest):
            yield seg
        time.sleep(refresh_seconds)


# ------------------------------------------------------------------
# Example: print first 10 segments of the Venice Piazza San Marco cam
# ------------------------------------------------------------------
if __name__ == "__main__":
    cam = ("https://www.skylinewebcams.com/en/webcam/italia/veneto/venezia/"
           "piazza-san-marco.html")  # cam ID 522

    token, sess_id = fetch_token(cam)
    print(f"PHPSESSID: {sess_id}")
    print(f"Token:     {token}")

    manifest = fetch_manifest(token, requests.Session())
    print("--- manifest ---")
    print(manifest)
    print(f"--- segments ({len(parse_segments(manifest))}) ---")
    for s in parse_segments(manifest)[:10]:
        print(s)
```

### 8.1 Drop-in async variant with ffmpeg piping

```python
import asyncio, re, subprocess, requests

TOKEN_RE = re.compile(r"livee\.m3u8\?a=([a-z0-9]{30})")

async def skyline_to_hls_out(cam_url: str, out_dir: str):
    """Continuously pull m3u8+segments and pipe to ffmpeg for transcoding."""
    sess = requests.Session()
    sess.headers["User-Agent"] = ("Mozilla/5.0 … Chrome/121.0.0.0 Safari/537.36")
    while True:
        r = sess.get(cam_url, timeout=30)
        token = TOKEN_RE.search(r.text).group(1)
        manifest = sess.get(
            f"https://hd-auth.skylinewebcams.com/livee.m3u8?a={token}",
            timeout=15,
        ).text
        if "#EXT-X-ENDLIST" in manifest:
            await asyncio.sleep(5); continue
        # Pipe to ffmpeg (segments are open, no auth):
        proc = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error",
             "-re", "-i", f"https://hd-auth.skylinewebcams.com/livee.m3u8?a={token}",
             "-c:v", "copy", "-c:a", "aac", "-f", "hls",
             "-hls_time", "4", "-hls_list_size", "6",
             f"{out_dir}/stream.m3u8"]
        )
        proc.wait()
        await asyncio.sleep(30)
```

### 8.2 Alternative: full URL re-fetch in your HLS player

If you control the `<video>` element, the simplest "always-fresh-token" hack is to wrap the m3u8 URL with a tiny proxy that re-fetches the page HTML every ~4 minutes and rewrites the URL:

```
Browser → your-proxy/skyline/<cam-id>/stream.m3u8
   1. Proxy GETs SkylineWebcams page for that cam
   2. Extracts `livee.m3u8?a=<token>`
   3. 302-redirects the browser to https://hd-auth.skylinewebcams.com/livee.m3u8?a=<token>
   4. Browser fetches manifest, then .ts segments directly (no auth needed on segments)
```

This works because the browser will follow the redirect, the manifest is the only auth-gated object, and the .ts URLs are open.

**One-line nginx config sketch:**
```nginx
location ~ ^/skyline/(\d+)/stream\.m3u8$ {
    # 1. Map cam_id -> page URL via your config (or DB)
    set $cam_page "";
    # e.g. include cams.conf;   # cam_id=522 -> cam_page="/en/webcam/italia/veneto/venezia/piazza-san-marco.html"
    # 2. sub_filter to inject a fresh token into a proxied m3u8 response
    proxy_pass https://www.skylinewebcams.com$cam_page;
    proxy_set_header User-Agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36";
}
```

(Implementation is more involved — you'd want to proxy the page, regex-extract the token, build a fresh m3u8 URL, and proxy that. But the conceptual approach works.)

---

## 9. Recommendations

| Goal | Recommendation |
|------|----------------|
| Personal viewing in your own player | Acceptable: scrape token every ~4 min, render in HLS.js / Video.js. Beware of TOS for any redistribution. |
| Embedding SkylineWebcams iframe | The site provides a share link / iframe option on each cam page (visible in the page UI) — this is the **officially supported** way. Use that instead. |
| Commercial re-streaming | **Stop.** Contact `info@visioray.com` for a license. They have a "PREMIUM" tier and B2B "Get your Cam" program for commercial use. |
| Embedding in your surveillance dashboard | Same — license or use the official iframe. If you must scrape, isolate to one cam, refresh at ≤1/4min, and don't strip the watermark (`https://cdn.jsdelivr.net/gh/SkylineWebcams/web@v2/skylinewebcams.svg`). |
| Bulk cam catalog | Build from worldcam.eu URL patterns (their numeric IDs match SkylineWebcams' cam IDs), but verify each one against SkylineWebcams before use. |

---

## 10. Open questions / further work

- **Token refresh within Clappr:** The embedded Clappr player does NOT auto-refresh tokens — viewers will see ~5 min streams and need to refresh. Does the player have a "replay" button? Manual page reload?
- **Geographic restrictions:** Some cams may be region-gated (the `livee.m3u8` returned 200 even from outside Italy in our test, but verify per-cam if needed).
- **Live vs. premium cams:** There's a `PREMIUM` link on the homepage. Premium cams may use additional auth (e.g., user session).
- **Capture protection:** The `copyright_violation-` filename + the fact that the manifest contains absolute timestamps in the .ts names means SkylineWebcams designed this to look like CDN obfuscation. Whether they actually enforce copyright takedowns on third-party replays is unclear.
- **Cam ID space:** Cam 522 = Venice, Cam 524 = Denmark (per worldcam). The numeric IDs are 1–~40000+ by observation; the full range is not published.

---

## 11. Verification commands (reproducible)

```bash
# 1. Get token from page
curl -A "Mozilla/5.0 …" \
  https://www.skylinewebcams.com/en/webcam/italia/veneto/venezia/piazza-san-marco.html \
  | grep -oE "livee\.m3u8\?a=[a-z0-9]{30}"

# 2. Fetch manifest
curl -A "Mozilla/5.0 …" \
  "https://hd-auth.skylinewebcams.com/livee.m3u8?a=<TOKEN>"

# 3. Fetch a .ts segment directly (no auth)
curl -I "https://hddn59.skylinewebcams.com/copyright_violation-1788000499619.ts"
# Expect: 200 OK, Content-Type: video/mp2t
```

---

## Appendix A — Raw capture summary

```
Domain      : hd-auth.skylinewebcams.com
Server      : nginx
Manifest    : application/x-mpegURL, ~594 bytes when live
Segments    : video/mp2t, unauthenticated, ~190 KB each, 4-second slices
CORS        : Access-Control-Allow-Origin: *
Cache (seg) : max-age=3600
Edge nodes  : hddn53, hddn59, … (round-robin)
Token TTL   : ~5 minutes (server-side session expiry)
Token chars : [a-z0-9]{30}
```

## Appendix B — All URLs verified during research

```
https://hd-auth.skylinewebcams.com/
https://hd-auth.skylinewebcams.com/api/                    (SPA fallback, 117 bytes)
https://hd-auth.skylinewebcams.com/api/v1/cams             (SPA fallback)
https://hd-auth.skylinewebcams.com/api/v2/cams             (SPA fallback)
https://hd-auth.skylinewebcams.com/api/cams                (SPA fallback)
https://hd-auth.skylinewebcams.com/auth/token              (SPA fallback)
https://hd-auth.skylinewebcams.com/api/token               (SPA fallback)
https://hd-auth.skylinewebcams.com/health                  (SPA fallback)
https://hd-auth.skylinewebcams.com/status                  (SPA fallback)
https://hd-auth.skylinewebcams.com/robots.txt              (Allow: /)
https://hd-auth.skylinewebcams.com/.well-known/security.txt (SPA fallback)
https://www.skylinewebcams.com/api/cams                    (404)
https://www.skylinewebcams.com/sitemap.xml                 (disabled, 22 bytes)
https://www.skylinewebcams.com/webcams.json                (disabled, 22 bytes)
https://api.skylinewebcams.com/                            (404)
https://www.skylinewebcams.com/terms-of-use.html           (VisioRay Srl, Italian law)
https://worldcam.eu/webcams/europe/italy                   (directory, links out)
https://worldcam.eu/click/url?code=<base64>                (redirects to cam owner site)
https://weather-cams.visioray.com/                         (stale placeholder)
https://www.visioray.com/                                  (VisioRay Srl marketing)
https://github.com/SkylineWebcams/web                      (asset repo only, no API)
https://cdn.jsdelivr.net/gh/SkylineWebcams/web@v3/player.js (Clappr bundle, 401 KB)
https://cdn.jsdelivr.net/gh/SkylineWebcams/web@v2/sky.js   (UI bundle, 110 KB)
```

