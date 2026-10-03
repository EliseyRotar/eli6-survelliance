# New Cams Added — Aug 22 02:00–03:30 UTC

**32 cams added** via continuous cam discovery pipeline. See `camera_testing/pipeline_log.txt`, `camera_testing/internetdb_log.txt` for raw trace.

## Index range
idx 285 through idx 316. CSV entry max_idx=316 (of 290 → 302 unique rows; some compacted).

## Source
- **insecam.org** country pages (50+ countries): the primary feed — 50 URLs/hr yielded 24-30 hits/round.
- **InternetDB ASN scan**: 1000 random IPs with port 80/81/8080/8443/554/8089 open → 0 yielded live cams (too generic — those ports are routers, not cams).
- insecam brands (Axis/Sony/Foscam/etc.) and cities pages return small consistent lists.

## Cams by country
| Country | Count | Cities |
|---------|-------|--------|
| Czechia | 2 | České Budějovice, Nový Malín |
| UK | 2 | Brighton (×2 different ports) |
| Poland | 3 | Stanisławice, Darłówko (×2) |
| Hungary | 2 | Csengele, Budapest |
| India | 2 | Hyderabad (×2) |
| Malaysia | 3 | Kuala Lumpur (×3) |
| Greece | 2 | Athens, Thessaloniki |
| Hong Kong | 2 | Lai Chi Kok, Yuen Long San Hui |
| USA | 2 | Mobile (AL), Rancho Cucamonga (CA) |
| South Africa | 2 | Johannesburg (×2 different ports) |
| Lithuania | 2 | Klaipėda, Vilnius |
| Slovakia | 1 | Rimavská Sobota |
| Spain | 1 | El Grao (Castellón) |
| Austria | 1 | Achenkirch |
| Norway | 1 | Verdal |
| Belgium | 1 | Ghent |
| Australia | 1 | Melbourne |
| Taiwan | 1 | Shetou |
| Slovenia | 1 | Ljubljana |

## Stream type
All are MJPEG JPEG-frame endpoints at `/cgi-bin/viewer/video.jpg` (Bosch/Canon/Panasonic pattern). Content length 5-50 KB per frame; frame-rate 5-15 fps.

## Direct browser-playable URLs
Most are directly browseable: paste URL in Chrome/Firefox and you see the cam's image updated every 1-3 seconds. Browsers don't natively play MJPEG so the image just refreshes. To get a real video stream, use VLC or ffplay (we already have scripts in `camera_testing/newcam_*.bat`).

## Files produced
- `camera_testing/new_cams_summary.csv` — exact rows added (32 entries).
- `camera_testing/pipeline_log.txt` — full log.
- `camera_testing/internetdb_log.txt` — Shodan InternetDB scan log.
- `docs/WAVE_1_INSECAM_FINDINGS.md` — first wave commentary.

## How to view
```powershell
# Individual cam (replace <idx> with cam #):
ffplay http://217.12.54.147:8080/cgi-bin/viewer/video.jpg

# Or batch scan (10 cams):
& 'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\newcam_<host>.bat'
```

## Quality notes
- All cams in this batch are **private residential or small-business cams** that happen to have public IPs with no auth. Use for **research/curiosity only**.
- Some may be temporarily down (uptime varies; expect 60-80% live ratio at any moment).
- They are mostly European.
