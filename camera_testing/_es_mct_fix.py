# -*- coding: utf-8 -*-
"""Session 47d - MeteoCat/SCT (mct.gencat.cat) catalog rectification.

Source of truth: WFS layer cite:mct2_cameres (info) joined with
cite:mct2_cam_punt_active (geometry) via punt.id_camera == info fid number.
Catalog artifact: camera_testing/_es_mct_catalog.json (216 cams, 130 w/ geom).

Actions:
- drop 94 disc_ rows (duplicate mct cameras already present as tv_ rows)
- keep/rectify 130 tv_ rows: name/coords/city/org from WFS, canonical image URL
- Terrassa city cams use their origin host (emap.terrassa.cat) from catalog url
- probe every final URL, fetch posters (gif -> jpg) for live ones
"""
import csv
import io
import json
import os
import re
import time
import urllib.request

from PIL import Image

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
CAT = os.path.join(ROOT, "camera_testing", "_es_mct_catalog.json")
STATE = os.path.join(ROOT, "camera_testing", "_es_mct_fix_state.json")
POSTER_DIR = os.path.join(ROOT, "web_viewer", "static", "posters")
LOCK = CSV + ".lock"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) eli6-surveillance-research/1.0"
MCT_IMG = "https://mct.gencat.cat/mct2bo/RenderService?sctidcam={fid_file}"
MCT_APP = "https://mct.gencat.cat/"


def http_get(url, timeout=18):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()


def build_catalog():
    cat = json.load(open(CAT, encoding="utf-8"))
    by_id = {}
    for v in cat.values():
        nf = str(v.get("nom_fitxer") or "").strip()
        if not nf:
            continue
        key = nf.lower().replace(".jpeg", "").replace(".jpg", "").replace(".gif", "")
        by_id[key] = v
    return by_id


def make_name(entry):
    road = (entry.get("codi_carretera") or "").strip()
    muni = (entry.get("nom_municipi") or "").strip()
    pk = entry.get("pk")
    nf = entry.get("nom_fitxer")
    if road and pk is not None:
        base = f"SCT {road} pk{pk} - {muni}"
    elif road:
        base = f"SCT {road} - {muni}"
    else:
        base = f"SCT camera {nf} - {muni}"
    return re.sub(r"\s+", " ", base).strip()


def final_url(entry):
    raw = str(entry.get("url") or "").strip()
    if "emap.terrassa.cat" in raw:
        return raw.split()[0].strip()
    return MCT_IMG.format(fid_file=entry["nom_fitxer"])


def main():
    if os.path.exists(LOCK):
        raise SystemExit("lock exists: " + LOCK)
    os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        by_id = build_catalog()
        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        mct_rows = {}
        for i, r in enumerate(rows):
            u = r["live_stream_url"] or r["url"] or ""
            if "mct.gencat.cat" not in u:
                continue
            m = re.search(r"(?:sctidcam|nom)=([A-Za-z0-9]+)", u)
            if not m:
                continue
            mct_rows.setdefault(m.group(1).lower(), []).append(i)

        drop_idx = set()
        survivors = []
        for key, idxs in mct_rows.items():
            kept = None
            for i in idxs:
                if rows[i]["csv_id"].startswith("disc_"):
                    drop_idx.add(i)
                else:
                    kept = i
            if kept is None:
                kept = idxs[0]
                for i in idxs:
                    if i != kept:
                        drop_idx.add(i)
            survivors.append((key, kept))

        assert len(survivors) == 130, f"expected 130 survivors, got {len(survivors)}"
        assert len(drop_idx) == 94, f"expected 94 drops, got {len(drop_idx)}"

        probes = {}
        new_rows = []
        rectified = []
        missing_poster = []
        for key, i in sorted(survivors, key=lambda t: rows[t[1]]["csv_id"]):
            entry = by_id.get(key)
            if entry is None:
                raise SystemExit(f"no catalog entry for {key} ({rows[i]['csv_id']})")
            url = final_url(entry)
            row = rows[i]
            row["project_name"] = make_name(entry)
            g = entry.get("geom")
            if not g:
                raise SystemExit(f"no geom for {key}")
            row["lat"] = f"{g[1]:.7f}".rstrip("0").rstrip(".")
            row["lon"] = f"{g[0]:.7f}".rstrip("0").rstrip(".")
            row["city"] = (entry.get("nom_municipi") or "").strip()
            row["region"] = "Catalunya"
            row["country"] = "Spain"
            row["org"] = "Servei Catala de Transit (SCT)"
            row["category"] = "traffic"
            row["type"] = "image"
            row["enabled"] = "True"
            row["live_stream_url"] = url
            row["url"] = MCT_APP
            row["live_status"] = ""
            row["location_precision"] = "precise"
            gs = row.get("geo_source") or ""
            tag = "src=mct-wfs"
            if tag not in gs:
                row["geo_source"] = (gs + "; " + tag).strip("; ") if gs else tag
            notes = row.get("notes") or ""
            extra = f"mct-id={entry['nom_fitxer']}; mct-fid={entry['fid']}; src=mct-wfs@2026-10-17"
            row["notes"] = (notes + "; " + extra).strip("; ") if notes else extra
            if "emap.terrassa.cat" in url:
                alt = MCT_IMG.format(fid_file=entry["nom_fitxer"])
                row["notes"] += f"; mct-alt={alt}"
            rectified.append(row["csv_id"])
            probes[i] = url

        live_idx = []
        dead = []
        for i, url in probes.items():
            ok = False
            for attempt in range(2):
                try:
                    status, ctype, data = http_get(url)
                    if status == 200 and len(data) > 3000 and (
                        data[:3] == b"\xff\xd8\xff"
                        or data[:6] in (b"GIF87a", b"GIF89a")
                        or data[:8] == b"\x89PNG\r\n\x1a\n"
                    ):
                        ok = True
                        cache = os.path.join(
                            ROOT, "camera_testing", "_es_cache", f"mct_{rows[i]['csv_id']}.bin"
                        )
                        os.makedirs(os.path.dirname(cache), exist_ok=True)
                        with open(cache, "wb") as cf:
                            cf.write(data)
                        break
                except Exception:
                    time.sleep(1.2)
            if ok:
                rows[i]["live_status"] = "live"
                live_idx.append(i)
            else:
                rows[i]["live_status"] = ""
                rows[i]["notes"] = (rows[i].get("notes") or "") + "; probe-failed@2026-10-17"
                dead.append(rows[i]["csv_id"])

        posters = 0
        poster_fail = []
        os.makedirs(POSTER_DIR, exist_ok=True)
        for i in live_idx:
            cache = os.path.join(ROOT, "camera_testing", "_es_cache", f"mct_{rows[i]['csv_id']}.bin")
            try:
                with open(cache, "rb") as cf:
                    data = cf.read()
                img = Image.open(io.BytesIO(data))
                img.load()
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                elif img.mode == "L":
                    img = img.convert("RGB")
                out = os.path.join(POSTER_DIR, f"{rows[i]['idx']}.jpg")
                img.save(out, "JPEG", quality=80)
                posters += 1
            except Exception as e:
                poster_fail.append((rows[i]["csv_id"], str(e)[:80]))

        final_rows = [r for j, r in enumerate(rows) if j not in drop_idx]
        assert len(final_rows) == len(rows) - 94
        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(final_rows)
        os.replace(tmp, CSV)

        state = {
            "date": "2026-10-17",
            "dropped_disc_rows": 94,
            "rectified": sorted(rectified),
            "live": len(live_idx),
            "dead": dead,
            "posters": posters,
            "poster_fail": poster_fail,
            "rows_before": len(rows),
            "rows_after": len(final_rows),
        }
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print(f"[mct] dropped=94 rectified={len(rectified)} live={len(live_idx)} dead={len(dead)} posters={posters} rows {len(rows)}->{len(final_rows)}")
        if poster_fail:
            print("poster_fail:", poster_fail[:5])
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
