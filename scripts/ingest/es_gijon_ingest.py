# -*- coding: utf-8 -*-
"""Session 47k - Ayuntamiento de Gijón official webcams ingest.

Sources (verified 2026-10-18):
- Page: www.gijon.es/es/turismo/webcams (Angular SPA)
- Headless Drupal API: drupal.gijon.es/es/webcams/?_format=json
  -> node 4508 field_bloques_de_contenido = 4 paragraphs
- Paragraphs: drupal.gijon.es/es/detalle_paragraph/?...&ids=(4216)|(3965)|(25997)|(66976)
  -> iframe embeds: 1x youtube.com/embed/<id>, 3x camstreamer.com/yt-embed/<hash>/<S-code>
- All 4 resolve to live YouTube broadcasts on channel
  UCGUbYgA8GKjBLZL_nujT7Xw (Ayuntamiento de Gijón - Xixón);
  oEmbed titles verified live=True 2026-10-18.

Notes:
- observa.gijon.es ODS tenant decommissioned (expired cert + 404 Huwise).
- Channel tabs expose no additional currently-live cams.
- All 4 ids absent from CSV (0 overlap incl. tv_133992/tv_180021/tv_133667).
- type=video -> no poster (gip precedent).
"""
import csv
import json
import os
import re
import subprocess
import tempfile

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "es_gijon_ingest_state.json")
CAT_OUT = os.path.join(ROOT, "camera_testing", "_gijon_catalog.json")
LOCK = CSV + ".lock"
T = os.environ.get("TEMP", r"C:\Windows\Temp")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
ORG = "Ayuntamiento de Gijón - Xixón"
SUBJ = "Live public camera"
CHANNEL = "UCGUbYgA8GKjBLZL_nujT7Xw"
DATE = "2026-10-18"

# Official page order (paragraph id): title from YouTube oEmbed, coords per notes.
CAMS = [
    {"para": 3965, "yt": "ncuuM-iMl3A", "name": "Gijón San Lorenzo",
     "sc": None, "src": "https://www.youtube.com/embed/ncuuM-iMl3A?rel=0",
     "lat": "43.541062", "lon": "-5.650062",
     "geo": "manual:beach-centroid", "prec": ""},
    {"para": 4216, "yt": "arVrUGnJRlc", "name": "Gijón San Lorenzo (S-7907)",
     "sc": "S-7907", "src": "https://camstreamer.com/yt-embed/31ffd3d8d7a921c/S-7907?rel=0",
     "lat": "43.541062", "lon": "-5.650062",
     "geo": "manual:beach-centroid", "prec": ""},
    {"para": 25997, "yt": "hAweouDR-vM", "name": "Gijón Playa San Lorenzo",
     "sc": "S-14546", "src": "https://camstreamer.com/yt-embed/41fc64dd6ad16cb/S-14546?rel=0",
     "lat": "43.541062", "lon": "-5.650062",
     "geo": "manual:beach-centroid", "prec": ""},
    {"para": 66976, "yt": "e3TFH0g1mvU",
     "name": "Gijón Playa Peña Rubia, Parque de la Providencia",
     "sc": "S-14543", "src": "https://camstreamer.com/yt-embed/879f2b2e877d3c1/S-14543?rel=0",
     "lat": "43.5519688", "lon": "-5.6234813",
     "geo": "nominatim", "prec": "nominatim-poi"},
]


def curl_text(url, timeout=40):
    fd, tmp = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    try:
        p = subprocess.run(
            ["curl", "-sL", "-A", UA, "--max-time", str(timeout), "-o", tmp,
             "-w", "%{http_code}|%{content_type}", url],
            capture_output=True, text=True, timeout=timeout + 10,
        )
        meta = (p.stdout or "").strip().split("|")
        code = int(meta[0]) if meta and meta[0].isdigit() else 0
        ctype = meta[1] if len(meta) > 1 else ""
        with open(tmp, "rb") as f:
            body = f.read()
        return code, ctype, body
    finally:
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
                raise SystemExit("state=done already (delete state file to rerun)")

        with open(CAT_OUT, "w", encoding="utf-8") as f:
            json.dump({"source": "drupal.gijon.es/es/webcams/?_format=json",
                       "fetched": DATE, "channel": CHANNEL, "count": len(CAMS),
                       "cams": CAMS}, f, ensure_ascii=False, indent=1)

        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        existing = {x for r in rows for x in (r.get("url"), r.get("live_stream_url")) if x}

        next_idx = max(int(x["idx"]) for x in rows) + 1
        new_rows, results = [], []
        for c in CAMS:
            watch = "https://www.youtube.com/watch?v=" + c["yt"]
            if watch in existing:
                results.append((c["yt"], c["name"], None, 0, "skip"))
                continue
            code, ctype, body = curl_text(watch, 40)
            html = body.decode("utf-8", "replace")
            live = code == 200 and (
                '"isLive":true' in html or '"isLiveContent":true' in html
                or '"isLiveBroadcast":true' in html)
            idx = next_idx
            notes = "yt-id=%s; src=drupal.gijon.es:webcams (node 4508); para=%d" % (
                c["yt"], c["para"])
            if c["sc"]:
                notes += "; camstreamer=%s" % c["sc"]
            if c["geo"] == "nominatim":
                notes += "; geocoded=Playa de Peñarrubia (OSM beach POI)"
            notes += "; channel=%s; %s@%s; lm=%s" % (CHANNEL, "live" if live else "dead", DATE, DATE)
            row = {f: "" for f in fieldnames}
            row.update({
                "idx": str(idx),
                "csv_id": "gij_%d" % idx,
                "project_name": c["name"],
                "url": watch,
                "live_stream_url": watch,
                "type": "video",
                "enabled": "True",
                "live_status": "live" if live else "",
                "http_status": str(code) if code else "",
                "content_type": ctype,
                "description": "%s (Ayuntamiento de Gijón - Xixón live webcam)" % c["name"],
                "category": "beach",
                "likely_subject": SUBJ,
                "country": "Spain",
                "region": "Asturias",
                "city": "Gijón",
                "lat": c["lat"],
                "lon": c["lon"],
                "location_precision": c["prec"],
                "geo_source": c["geo"],
                "org": ORG,
                "host": "www.youtube.com",
                "confidence": "high",
                "notes": notes,
                "visibility": "",
            })
            new_rows.append(row)
            results.append((c["yt"], c["name"], live, code, len(body)))
            next_idx += 1

        rows.extend(new_rows)
        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV)

        added = [r for r in results if r[2] is not None and r[2] != "skip"]
        state = {
            "date": DATE, "phase": "done",
            "ingested": [x[0] for x in added],
            "live": sum(1 for x in added if x[2]),
            "rows_after": len(rows),
            "skipped_existing": [x[0] for x in results if x[2] == "skip"],
        }
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print("[gijon] ingested=%d live=%d total=%d" % (
            len(added), state["live"], len(rows)))
        for yt, nm, live, code, sz in results:
            print("  %s %s %s code=%s %sB" % (
                yt, nm, "skip" if live == "skip" else ("live" if live else "DEAD"), code, sz))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
