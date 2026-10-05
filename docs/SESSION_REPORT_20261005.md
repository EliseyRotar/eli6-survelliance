# Session 42 — 2026-10-05

Keyless source expansion (Shodan guest scrape + Netlas), CSV data repair,
visibility re-classification, dashboard verification.

## Sources & yield

### Shodan guest scrape (Playwright, no account)
- 19 chunk files in `camera_testing/shd_chunk_*.json`, 309 results,
  ~25 unique queries (webcamxp, go2rtc, dahua, reolink, snapshot.cgi,
  video.jpg, axis-cgi, vivotek, Live View/- AXIS, mjpeg camera, …).
- `scripts/ingest/shd_ingest.py` probes candidates, ingests verified
  still/stream endpoints with `csv_id_prefix=shd`.
- Result: **+38 rows** (`shd_*` provenance). Highlights: Hikvision ISAPI
  snapshots on odd high ports (Alibaba/Huawei cloud ranges), webcamXP
  `cam_1.cgi` on legacy ISP hosts.
- Hit rate: 322 candidates probed → 38 verified (12%). Failures are
  dominated by 5–12s connection timeouts on honeypot/dead IPs.

### Netlas (API, anonymous tier)
- `scripts/ingest/netlas_ingest_v2.py` (v2.1) resumed from
  `netlas_v2_progress.json`, Q0→Q30 of 1540 queries.
- Result: **+21 rows** (`nls_*`). Heavy 429 throttling (120→480s backoff)
  plus one DNS outage stop (18:02) — relaunched and running at session end.
- Fixed mid-session: `JUNK_IMG_RE` was missing `qrcode` etc.; one QR-code
  PNG (`nls_238611`, TP-Link modem setup page misdetected as cam) was
  ingested before the fix and removed in the repair pass.

### Net result
230,033 → **230,091 rows** (+59 added, −1 junk row removed).

## Phase 3 — other keyless engines (negative result)
- ZoomEye `.hk` — transport error; `.org` — HTTP 521.
- Hunter.how — JS app, results behind sign-in.
- FOFA / Censys — known login-walled.
- **Conclusion: all alternative engines require accounts.** Next yield step
  is either a Shodan API key (1 credit/query tier covers ~1k queries) or a
  free ZoomEye/FOFA account.

## Phase 4 — CSV repair (`scripts/fix/repair_session42.py`)
Backup: `backups/session42_20261005_221123/`. Row count verified before/after.

| Fix | Count |
|---|---|
| `live_stream_url` junk ('video','image', text) → replaced with valid `url` | 1,699 |
| invalid-scheme `url` cleared (and live cleared with it) | 86 |
| JSON-escaped `\/` in URL fields unescaped | 6 |
| junk QR row removed | 1 |

Non-fixes confirmed safe: cross-host `live_stream_url` (cdn.skylinewebcams.com
pattern) is legitimate — no rule added for it.

## Phase 5 — classification + API + dashboard
`scripts/fix/classify_visibility.py` re-run (report regenerated):

| visibility | S41 | S42 |
|---|---|---|
| public | 229,919 | **229,950** |
| private | 113 | **136** |
| unknown | 1 | **5** |

Rule totals: U1 139,899 · U2 87,909 · U4 1,144 · U5 975 · P7 119 ·
U3 23 · P4 12 · P1 5 · no-rule 5.

API (`:8773`):
- Discovered **stale index**: SQLite held 106,505 rows (auto-reload is
  intentionally disabled). `GET /api/refresh` → ok, rows=230,091.
- `/api/stats`: total 230,091 · live 208,379 ·
  `by_visibility {private 136, public 229,950, unknown 5}`.
- Buckets: `/api/cams?visibility=private` → 136, `=unknown` → 5. ✓

Dashboard (agent-browser): visibility chips show
`all 208k / public 208k / private 136 / unknown 5` — private/unknown match
API exactly; tiles render with LIVE/TIMEOUT/ERR badges.

## Bug fixes
- `camera_testing/poster_ffmpeg.py`: `log()` rejected `flush=True`
  (TypeError at launch) → `def log(msg, **kwargs)`. Relaunched; batch of
  1,883 poster jobs completed (5 ok / 1,878 dead HLS upstreams, 4.4 min).
- `JUNK_IMG_RE` qrcode/qr-code/qr_code//qr//watermark/overlay added.
- `camera_testing/csv_writer.py`: `csv_id_prefix` support (nls/shd
  provenance instead of hardcoded `disc_`).

## Background services at session end
- netlas_ingest: PID 31272 (429 backoff, resuming Q30/1540)
- cam_reaper: probe cycles ongoing (~cycle 2051, alive=875)
- argus_geocode: finished (875 cams)
- poster_ffmpeg: finished (batch complete)
- run_dashboard (16572) + app.py (15288, :8773): healthy

## Known flags
- `idx 238628` — WordPress `/static/uploads/…WhatsApp-Image…` passed probe
  (image ≥2KB); likely not a camera stream. Kept; revisit with poster
  scene analysis or remove next repair pass.

## Git
- Session 41 leftovers uncommitted at start (classify FP fixes,
  visibility drawer, csv_id_prefix, poster fix, chunks, report).
- Committed together with this report as
  `Session 42: keyless sources + CSV repair + visibility reclass`.
