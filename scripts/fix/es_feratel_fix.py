# -*- coding: utf-8 -*-
"""Session 47l - Spain/Andorra feratel rows: mirror->public-hotspot fix + 3 ingest.

Sources (verified 2026-10-18):
- Official: sierranevada.es/en-directo/webcams embeds feratel webtv
  cams 15110-15114 + official snapshot recursos.sierranevada.es
  (.../pradollano/snap_c1.jpg, Last-Modified minute-fresh).
- feratel titles/coords: webtv.feratel.com/webtv/?design=v5&cam=<id>
  (<title> = 'feratel MediaPlayer | Livecam <name>-Webcam ...').
- Public frames: webtvhotspot.feratel.com/hotspot/37/<id>/0.jpeg?design=v3
  (200 image/jpeg for all 23 ES/AD ids; Last-Modified advances ~45s =
  live; identical md5 db70616d... across 15110/15114/15080/76100 =
  German placeholder 'Derzeit ist kein aktuelles Bild verfugbar.' ->
  offline). Watermarks+clock verify live frames (e.g. Veleta 05:29).

Phase A: 21 Spain/Andorra rows (trafficvision_id=feratel:feratel-<id>)
  flip from media.trafficvision.live mirror (403 auth_required,
  'forbidden' / referer 'upstream 410') to public feratel hotspot jpg:
  url/type/content_type/live_status, region filled, operator-verbatim
  webtv title, geo_source, notes keep old mirror + trafficvision_id.
Phase B: ingest 3 missing: 15110 Zona Laguna (placeholder -> ''),
  15112 Zona Veleta (live), official Pradollano snapshot (live).
"""
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile

from PIL import Image

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "es_feratel_fix_state.json")
CAT_OUT = os.path.join(ROOT, "camera_testing", "_sn_feratel_catalog.json")
HOT_DIR = os.path.join(ROOT, "camera_testing", "_sn_hotspot")
POSTER_DIR = os.path.join(ROOT, "web_viewer", "static", "posters")
LOCK = CSV + ".lock"
T = os.environ.get("TEMP", r"C:\Windows\Temp")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DATE = "2026-10-18"
SUBJ = "Live public camera"

REGION_BY_ID = {
    # Andorra (Grandvalira / Vallnord)
    15030: "Andorra", 15031: "Andorra", 15040: "Andorra", 15045: "Andorra",
    15050: "Andorra", 15055: "Andorra", 15056: "Andorra", 15060: "Andorra",
    15061: "Andorra", 15065: "Andorra", 15090: "Andorra", 76100: "Andorra",
    # Spain
    15024: "Aragón", 15083: "Aragón", 15080: "Aragón",          # Panticosa/Cerler
    15100: "Catalunya", 15010: "Catalunya",                       # Boí Taüll/Cambrils
    15111: "Andalucía", 15113: "Andalucía", 15114: "Andalucía",  # Sierra Nevada
    15115: "Illes Balears (Balearic Islands)",                    # Cala Santanyí
}

HOTSPOT = "https://webtvhotspot.feratel.com/hotspot/37/%d/0.jpeg?design=v3"
PRADOLLANO = ("https://recursos.sierranevada.es/_extras/fotos_camaras/"
              "pradollano/snap_c1.jpg")

INGEST = [
    {"id": 15110, "name": "Sierra Nevada - Zona Laguna", "region": "Andalucía",
     "city": "Monachil", "src": HOTSPOT % 15110, "geo": "src:webtv.feratel.com",
     "prec": "precise", "lat": "37.058909", "lon": "-3.39374"},
    {"id": 15112, "name": "Sierra Nevada - Zona Veleta", "region": "Andalucía",
     "city": "Monachil", "src": HOTSPOT % 15112, "geo": "src:webtv.feratel.com",
     "prec": "precise", "lat": "37.062669", "lon": "-3.373692"},
    {"id": None, "name": "Pradollano", "region": "Andalucía",
     "city": "Pradollano", "src": PRADOLLANO, "geo": "nominatim",
     "prec": "nominatim-poi", "lat": "37.0943309", "lon": "-3.3990897"},
]


def curl_jpeg(url, timeout=30):
    fd, tmp = tempfile.mkstemp(suffix=".jpg")
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


def webtv_name(title):
    if not title:
        return None
    part = title.split("Livecam ", 1)
    if len(part) < 2:
        return None
    return part[1].split("-Webcam")[0].strip() or None


def main():
    if os.path.exists(LOCK):
        raise SystemExit("lock exists: " + LOCK)
    lock_fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(lock_fd)
    try:
        if os.path.exists(STATE):
            st = json.load(open(STATE, encoding="utf-8"))
            if st.get("phase") == "done":
                raise SystemExit("state=done already (delete state to rerun)")

        fer = json.load(open(os.path.join(T, "sn_feratel_all.json"), encoding="utf-8"))
        with open(CAT_OUT, "w", encoding="utf-8") as f:
            json.dump({"source": ["webtv.feratel.com (titles/coords)",
                                  "webtvhotspot.feratel.com (frames)",
                                  "sierranevada.es/en-directo/webcams",
                                  "recursos.sierranevada.es (pradollano)"],
                       "fetched": DATE, "count": len(fer), "cams": fer},
                      f, ensure_ascii=False, indent=1)

        # placeholder = identical bodies (German 'no image' card)
        ph_md5 = hashlib.md5(open(os.path.join(HOT_DIR, "hs_15110_0.jpg"), "rb").read()).hexdigest()
        live_md5 = {}
        for cid in fer:
            p = os.path.join(HOT_DIR, "hs_%s_0.jpg" % cid)
            if os.path.exists(p):
                live_md5[cid] = hashlib.md5(open(p, "rb").read()).hexdigest() != ph_md5

        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        # ---------- Phase A: rectify ----------
        fixed = 0
        for r in rows:
            m = re.search(r"trafficvision_id=feratel:feratel-(\d+)", r.get("notes") or "")
            if not m:
                continue
            cid = int(m.group(1))
            if str(cid) not in fer or cid not in REGION_BY_ID:
                continue
            if "hotspot-flip@" + DATE in (r.get("notes") or ""):
                continue
            meta = fer[str(cid)]
            name = webtv_name(meta.get("webtv_title"))
            old_url = r.get("url") or ""
            if name:
                r["project_name"] = name
            r["url"] = HOTSPOT % cid
            r["live_stream_url"] = HOTSPOT % cid
            r["type"] = "image"
            r["http_status"] = "200"
            r["content_type"] = "image/jpeg"
            is_live = live_md5.get(str(cid), True)
            r["live_status"] = "live" if is_live else ""
            r["region"] = REGION_BY_ID[cid]
            r["geo_source"] = "src:webtvhotspot.feratel.com"
            notes = r.get("notes") or ""
            ph_note = "" if is_live else "; hotspot-placeholder-no-image@%s" % DATE
            r["notes"] = notes + (
                "; feratel-title=%s; old-mirror=%s (auth_required); "
                "hotspot-frame=0; hotspot-flip@%s%s" % (
                    name or "?", old_url, DATE, ph_note))
            fixed += 1

        # ---------- Phase B: ingest 3 ----------
        next_idx = max(int(x["idx"]) for x in rows) + 1
        new_rows, results, posters = [], [], 0
        existing_urls = {x for rr in rows for x in (rr.get("url"), rr.get("live_stream_url")) if x}
        os.makedirs(POSTER_DIR, exist_ok=True)
        for spec in INGEST:
            if spec["src"] in existing_urls:
                results.append((spec["name"], "skip"))
                continue
            code, ctype, body = curl_jpeg(spec["src"], 30)
            md5 = hashlib.md5(body).hexdigest()
            live = code == 200 and len(body) > 3000 and md5 != ph_md5
            cid = spec["id"]
            meta = fer.get(str(cid)) if cid else {}
            notes = ""
            if cid:
                notes = "feratel-cam-id=%d; webtv-title=%s; src=sierranevada.es:en-directo/webcams" % (
                    cid, meta.get("webtv_title") or "?")
            else:
                notes = "src=sierranevada.es:en-directo/webcams; watermark=Zona Pradollano-Rio; geocoded=Pradollano hamlet (OSM)"
            notes += "; hotspot-frame=0" if cid else ""
            notes += "; live-checked@%s" % DATE
            if not live:
                notes += "; hotspot-placeholder-no-image@%s" % DATE
            idx = next_idx
            row = {f: "" for f in fieldnames}
            row.update({
                "idx": str(idx),
                "csv_id": "sn_%d" % idx,
                "project_name": spec["name"],
                "url": spec["src"],
                "live_stream_url": spec["src"],
                "type": "image",
                "enabled": "True",
                "live_status": "live" if live else "",
                "http_status": str(code) if code else "",
                "content_type": ctype,
                "description": "%s webcam (Sierra Nevada ski area)" % spec["name"],
                "category": "mountain",
                "likely_subject": SUBJ,
                "country": "Spain",
                "region": spec["region"],
                "city": spec["city"],
                "lat": spec["lat"],
                "lon": spec["lon"],
                "location_precision": spec["prec"],
                "geo_source": spec["geo"],
                "org": "Sierra Nevada (CETURSA)",
                "host": "webtvhotspot.feratel.com" if cid else "recursos.sierranevada.es",
                "confidence": "high",
                "notes": notes,
                "visibility": "",
            })
            if live:
                img = Image.open(io.BytesIO(body))
                img.load()
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(os.path.join(POSTER_DIR, "%s.jpg" % row["idx"]), "JPEG", quality=80)
                posters += 1
            new_rows.append(row)
            results.append((spec["name"], "live" if live else "DEAD"))
            next_idx += 1

        rows.extend(new_rows)
        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV)

        state = {"date": DATE, "phase": "done", "rectified": fixed,
                 "ingested": [r["csv_id"] for r in new_rows],
                 "live_new": sum(1 for _, s in results if s == "live"),
                 "posters": posters, "rows_after": len(rows),
                 "placeholder_md5": ph_md5}
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print("[feratel] rectified=%d ingested=%d (live=%d) posters=%d total=%d" % (
            fixed, len(new_rows), state["live_new"], posters, len(rows)))
        for nm, s in results:
            print("  %-40s %s" % (nm, s))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
