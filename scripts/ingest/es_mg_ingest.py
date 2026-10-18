# -*- coding: utf-8 -*-
"""Session 47i - MeteoGalicia (Xunta de Galicia) rectify + ingest.

Sources (verified 2026-10-18):
- JSON: servizos.meteogalicia.gal/mgrss/observacion/jsonCamaras.action
  (33 cams; NOTE current path is `mgrss`, documented `mg/rss` is 404;
  found via Angular chunk-A6AZO46B.js)
- ArcGIS: ideg.xunta.gal/.../METEO2_WS/Camaras/MapServer/0 (34 feats =
  JSON33 + dir=Radar -> Xesteiras/Cuntis)
- Image: www.meteogalicia.gal/datosred/camaras/{Group}/{Dir}/ultima.jpg

Phase A: rectify 31 disc_ Argus rows (junk title/region/city/address +
  shared bogus coords 42.555164,-9.028601) from JSON; radar row from
  ArcGIS (absent from JSON, 3084B placeholder -> live_status='');
  tv_102089 city 'Viveiro (Nursery)' -> 'Viveiro'.
Phase B: ingest 2 missing cams (ciesfarosur, onsplaya) as mg_ + posters.
"""
import csv
import json
import os
import re
import subprocess
import tempfile

from PIL import Image

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "es_mg_ingest_state.json")
CAT_OUT = os.path.join(ROOT, "camera_testing", "_mg_catalog.json")
POSTER_DIR = os.path.join(ROOT, "web_viewer", "static", "posters")
LOCK = CSV + ".lock"
T = os.environ.get("TEMP", r"C:\Windows\Temp")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
IMAGE_MAGIC = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")
ORG = "MeteoGalicia (Xunta de Galicia)"
SUBJ = "Live public camera"
RECT_MARK = "mg-rectified@2026-10-18"


def curl_bytes(url, timeout=30):
    fd, tmp = tempfile.mkstemp(suffix=".bin")
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
        return code, (ctype or "").split(";")[0].strip(), body
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def dirn(u):
    m = re.search(r"datosred/camaras/(\w+)/([\w\d]+)/ultima\.jpg", u or "")
    return (m.group(1), m.group(2).lower()) if m else None


def main():
    if os.path.exists(LOCK):
        raise SystemExit("lock exists: " + LOCK)
    lock_fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(lock_fd)
    try:
        state = {}
        if os.path.exists(STATE):
            state = json.load(open(STATE, encoding="utf-8"))
        if state.get("phase") == "done":
            raise SystemExit("state=done already (delete state file to rerun)")

        js = json.load(open(os.path.join(T, "mg_camaras.json"), encoding="utf-8"))["listaCamaras"]
        arc = json.load(open(os.path.join(T, "mg_arcgis.json"), encoding="utf-8"))
        assert len(js) == 33, len(js)
        with open(CAT_OUT, "w", encoding="utf-8") as f:
            json.dump({"source": "servizos.meteogalicia.gal/mgrss/observacion/jsonCamaras.action",
                       "fetched": "2026-10-18", "count": len(js),
                       "arcgis_count": len(arc["features"]), "listaCamaras": js},
                      f, ensure_ascii=False, indent=1)

        json_by_dir = {dirn(c["imaxeCamara"]): c for c in js}
        arc_by_dir = {f["attributes"]["Directorio"].lower(): f["attributes"] for f in arc["features"]}

        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        # ---------- Phase A: rectify ----------
        fixed, fixed_tv, radar_id = 0, 0, None
        for r in rows:
            u = (r.get("live_stream_url") or "") + " " + (r.get("url") or "")
            k = dirn(u)
            notes = r.get("notes") or ""
            if not k:
                if r["csv_id"] == "tv_102089" and r.get("city") != "Viveiro":
                    r["city"] = "Viveiro"
                    fixed_tv += 1
                continue
            grp, d = k
            if RECT_MARK in notes:
                continue
            if d == "radar":
                a = arc_by_dir.get("radar")
                if not a:
                    continue
                r["project_name"] = a["Nome"]
                r["region"] = "Galicia"
                r["city"] = a["concello"]
                r["address"] = ""
                r["road"] = ""
                r["lat"] = str(a["lat"])
                r["lon"] = str(a["lon"])
                r["location_precision"] = "precise"
                r["geo_source"] = "src:ideg.xunta.gal:Camaras"
                r["description"] = "MeteoGalicia webcam (%s, %s) - placeholder image, not live" % (
                    a["concello"], a["provincia"])
                r["likely_subject"] = SUBJ
                r["live_status"] = ""
                r["org"] = ORG
                r["confidence"] = "high"
                r["notes"] = (notes + "; " if notes else "") + (
                    "arcgis-webcam-id=%s; dir=Radar; placeholder-3084b@2026-10-18; "
                    "not-in-json-catalog@2026-10-18; %s" % (a["idWebcam"], RECT_MARK))
                fixed += 1
                radar_id = r["csv_id"]
                continue
            c = json_by_dir.get(k)
            if not c:
                continue
            r["project_name"] = c["nomeCamara"]
            r["region"] = "Galicia"
            r["city"] = c["concello"]
            r["address"] = ""
            r["road"] = ""
            r["lat"] = str(c["lat"])
            r["lon"] = str(c["lon"])
            r["location_precision"] = "precise"
            r["geo_source"] = "src:servizos.meteogalicia.gal"
            r["description"] = "MeteoGalicia webcam (%s, %s)" % (c["concello"], c["provincia"])
            r["likely_subject"] = SUBJ
            r["org"] = ORG
            r["confidence"] = "high"
            r["notes"] = (notes + "; " if notes else "") + (
                "mg-webcam-id=%s; src=mgrss-json; rectified=2026-10-18; %s" % (
                    c["identificador"], RECT_MARK))
            fixed += 1

        # ---------- Phase B: ingest 2 ----------
        next_idx = max(int(x["idx"]) for x in rows) + 1
        new_rows, results = [], []
        for c in sorted(js, key=lambda x: x["nomeCamara"]):
            k = dirn(c["imaxeCamara"])
            if any(dirn((x.get("live_stream_url") or "") + " " + (x.get("url") or "")) == k
                   for x in rows):
                continue
            code, ctype, body = curl_bytes(c["imaxeCamara"], 30)
            live = code == 200 and len(body) > 3000 and any(
                body[:len(m)] == m for m in IMAGE_MAGIC)
            idx = next_idx
            row = {f: "" for f in fieldnames}
            row.update({
                "idx": str(idx),
                "csv_id": "mg_%04d" % idx,
                "project_name": c["nomeCamara"],
                "url": c["imaxeCamara"],
                "live_stream_url": c["imaxeCamara"],
                "type": "image",
                "enabled": "True",
                "live_status": "live" if live else "",
                "http_status": str(code) if code else "",
                "content_type": ctype,
                "description": "MeteoGalicia webcam (%s, %s)" % (c["concello"], c["provincia"]),
                "category": "scenic",
                "likely_subject": SUBJ,
                "country": "Spain",
                "region": "Galicia",
                "city": c["concello"],
                "location_precision": "precise",
                "lat": str(c["lat"]),
                "lon": str(c["lon"]),
                "geo_source": "src:servizos.meteogalicia.gal",
                "org": ORG,
                "host": "www.meteogalicia.gal",
                "confidence": "high",
                "notes": "mg-webcam-id=%s; dir=%s; src=mgrss-json; data-ultima-act=%s; lm=2026-10-18" % (
                    c["identificador"], k[1], c.get("dataUltimaAct") or ""),
                "visibility": "",
            })
            new_rows.append(row)
            results.append((row["csv_id"], c["nomeCamara"], live, code, len(body)))
            next_idx += 1

        posters = 0
        os.makedirs(POSTER_DIR, exist_ok=True)
        for row, res in zip(new_rows, results):
            if not res[2]:
                continue
            code, _, body = curl_bytes(row["live_stream_url"], 30)
            if code == 200 and any(body[:len(m)] == m for m in IMAGE_MAGIC):
                img = Image.open(__import__("io").BytesIO(body))
                img.load()
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(os.path.join(POSTER_DIR, "%s.jpg" % row["idx"]), "JPEG", quality=80)
                posters += 1

        rows.extend(new_rows)
        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV)

        state.update({
            "date": "2026-10-18", "phase": "done",
            "rectified_json": fixed, "rectified_tv_city": fixed_tv,
            "radar_row": radar_id,
            "ingested": [x[0] for x in results],
            "live": sum(1 for x in results if x[2]),
            "posters": posters,
            "rows_after": len(rows),
        })
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print("[mg] rectified=%d (radar=%s) tv_city_fix=%d ingested=%d live=%d posters=%d total=%d" % (
            fixed, radar_id, fixed_tv, len(results), state["live"], posters, len(rows)))
        for cid, nm, l, code, sz in results:
            print("  %s %s %s code=%s %sB" % (cid, nm, "live" if l else "DEAD", code, sz))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
