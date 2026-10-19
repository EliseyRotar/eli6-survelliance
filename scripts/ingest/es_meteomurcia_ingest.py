# -*- coding: utf-8 -*-
"""Session 47m - MeteoMurcia.com (Puente Tocinos, Murcia) ingest.

Sources (verified 2026-10-19):
- www.meteomurcia.com/webcam.php embeds (DOM order, captions follow embed):
  * YouTube CGNR241h08Q  = Webcam 1, Cámara PTZ robotizada 360°
    (og:title 'MeteoMurcia.com en DIRECTO. Cámara robotizada (PTZ)...',
    live, channel UCG3TWlJ9eh4n7-zNXNfPISg 'MeteoMurcia.com')
  * camsecure wmcam.html = Webcam 2, fija Oeste-Suroeste
    -> HLS https://camsecure.co/HLS/murcia.m3u8 (200 live, segmenting)
  * camsecure xmcam.html = Webcam 3, fija Este-Sureste
    -> HLS https://camsecure.co/HLS/murcia2.m3u8 (200 live)
  * YouTube L1rgJ3gI2Eg  = composición webcams 2+3 (live, same channel)
- webcammurcia.com Av. Libertad cam already in CSV (live avlibertad.jpg,
  row matched by url = trafficvision webcammurcia-avlibertad); enrich
  notes with windy cross-listing id 1334517004.
- Coords: OSM 'Puente Tocinos' suburb 37.9929006,-1.1022155 (station
  neighborhood; no public station coords on page).
"""
import csv
import json
import os
import re
import subprocess
import tempfile

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "es_meteomurcia_state.json")
LOCK = CSV + ".lock"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DATE = "2026-10-19"
SUBJ = "Live public camera"
LAT, LON = "37.9929006", "-1.1022155"

CAMS = [
    {"name": "MeteoMurcia - Webcam 2 (Oeste-Suroeste)",
     "url": "https://camsecure.co/HLS/murcia.m3u8", "kind": "hls",
     "desc": "MeteoMurcia.com webcam fija Oeste-Suroeste (Puente Tocinos, Murcia)",
     "notes": "src=meteomurcia.com:webcam.php; iframe=wmcam.html; hls=camsecure.co:HLS/murcia; "
              "webcam=2-fija-oeste; neighborhood=Puente Tocinos"},
    {"name": "MeteoMurcia - Webcam 3 (Este-Sureste)",
     "url": "https://camsecure.co/HLS/murcia2.m3u8", "kind": "hls",
     "desc": "MeteoMurcia.com webcam fija Este-Sureste (Puente Tocinos, Murcia)",
     "notes": "src=meteomurcia.com:webcam.php; iframe=xmcam.html; hls=camsecure.co:HLS/murcia2; "
              "webcam=3-fija-este; neighborhood=Puente Tocinos"},
    {"name": "MeteoMurcia - Cámara PTZ",
     "url": "https://www.youtube.com/watch?v=CGNR241h08Q", "kind": "yt",
     "yt": "CGNR241h08Q",
     "desc": "MeteoMurcia.com en DIRECTO. Cámara robotizada (PTZ). Meteorología ciudad de Murcia, "
             "en TIEMPO REAL",
     "notes": "src=meteomurcia.com:webcam.php; webcam=1-ptz-360; channel=UCG3TWlJ9eh4n7-zNXNfPISg; "
              "neighborhood=Puente Tocinos"},
    {"name": "MeteoMurcia - Composición Webcam 2+3",
     "url": "https://www.youtube.com/watch?v=L1rgJ3gI2Eg", "kind": "yt",
     "yt": "L1rgJ3gI2Eg",
     "desc": "MeteoMurcia.com en directo. Meteorología de la ciudad de Murcia, en TIEMPO REAL "
             "(composición de las webcams 2 y 3)",
     "notes": "src=meteomurcia.com:webcam.php; webcam=composicion-2+3; "
              "channel=UCG3TWlJ9eh4n7-zNXNfPISg; neighborhood=Puente Tocinos"},
]


def curl(url, out=None, timeout=35):
    args = ["curl", "-sL", "-A", UA, "--max-time", str(timeout)]
    tmp = None
    if not out:
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        out = tmp
    args += ["-o", out, "-w", "%{http_code}|%{content_type}", url]
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout + 10)
        meta = (p.stdout or "").strip().split("|")
        code = int(meta[0]) if meta and meta[0].isdigit() else 0
        ctype = meta[1] if len(meta) > 1 else ""
        with open(out, "rb") as f:
            body = f.read()
        return code, ctype, body
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass


def main():
    if os.path.exists(LOCK):
        raise SystemExit("lock exists: " + LOCK)
    lock_fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(lock_fd)
    try:
        if os.path.exists(STATE):
            st = json.load(open(STATE, encoding="utf-8"))
            if st.get("phase") == "done":
                raise SystemExit("state=done already")

        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        existing = {x for r in rows for x in (r.get("url"), r.get("live_stream_url")) if x}

        # ---- tiny rectify: webcammurcia row notes += windy id ----
        windy_fixed = 0
        for r in rows:
            if (r.get("url") or "") == "https://www.webcammurcia.com/avlibertad.jpg" \
                    and "windy-id=1334517004" not in (r.get("notes") or ""):
                r["notes"] = (r.get("notes") or "") + "; windy-id=1334517004; enriched@" + DATE
                windy_fixed += 1

        next_idx = max(int(x["idx"]) for x in rows) + 1
        new_rows, results = [], []
        for c in CAMS:
            if c["url"] in existing:
                results.append((c["name"], "skip"))
                continue
            code, ctype, body = curl(c["url"])
            if c["kind"] == "hls":
                live = code == 200 and body.lstrip()[:7] == b"#EXTM3U"
            else:
                html = body.decode("utf-8", "replace")
                live = code == 200 and (
                    '"isLive":true' in html or '"isLiveContent":true' in html)
            idx = next_idx
            row = {f: "" for f in fieldnames}
            row.update({
                "idx": str(idx),
                "csv_id": "mmu_%d" % idx,
                "project_name": c["name"],
                "url": c["url"],
                "live_stream_url": c["url"],
                "type": "video",
                "enabled": "True",
                "live_status": "live" if live else "",
                "http_status": str(code) if code else "",
                "content_type": ctype,
                "description": c["desc"],
                "category": "city",
                "likely_subject": SUBJ,
                "country": "Spain",
                "region": "Murcia",
                "city": "Murcia",
                "lat": LAT,
                "lon": LON,
                "location_precision": "nominatim-poi",
                "geo_source": "nominatim",
                "org": "MeteoMurcia.com",
                "host": "camsecure.co" if c["kind"] == "hls" else "www.youtube.com",
                "confidence": "high",
                "notes": c["notes"] + "; live-checked@%s" % DATE
                         + ("; yt-id=%s" % c["yt"] if c.get("yt") else ""),
                "visibility": "",
            })
            new_rows.append(row)
            results.append((c["name"], "live" if live else "DEAD (code=%s)" % code))
            next_idx += 1

        rows.extend(new_rows)
        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV)

        state = {"date": DATE, "phase": "done",
                 "windy_notes_enriched": windy_fixed,
                 "ingested": [r["csv_id"] for r in new_rows],
                 "live": sum(1 for _, s in results if s == "live"),
                 "rows_after": len(rows)}
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print("[meteomurcia] windy_enrich=%d ingested=%d live=%d total=%d" % (
            windy_fixed, len(new_rows), state["live"], len(rows)))
        for nm, s in results:
            print("  %-46s %s" % (nm, s))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
