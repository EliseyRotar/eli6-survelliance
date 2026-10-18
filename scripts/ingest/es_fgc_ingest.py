# -*- coding: utf-8 -*-
"""Session 47e - FGC tourist webcams ingest from dadesobertes.fgc.cat (ODS).

Source: analisi.transparenciacatalunya.cat href dataset 739g-m9dx ->
https://dadesobertes.fgc.cat/explore/dataset/webcams-actives-tim/table/
ODS API: /api/records/1.0/search/?dataset=webcams-actives-tim (30 records,
all is_active=1): fields name_bu/nom_servei/url/coordenadas([lat,lon])/imatge_2.

Image resolution:
- direct jpg urls (projecte4estacions, pirineu365, turismefgc, feratel): probe as-is
- roundshot pages: og:image -> /cams/{n} absolute (live JPEG)
- fallback: ODS file api /api/datasets/1.0/webcams-actives-tim/files/{fileid}
"""
import csv
import io
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.parse

from PIL import Image

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
CAT = os.path.join(ROOT, "camera_testing", "_es_fgc_catalog.json")
STATE = os.path.join(ROOT, "camera_testing", "es_fgc_ingest_state.json")
POSTER_DIR = os.path.join(ROOT, "web_viewer", "static", "posters")
LOCK = CSV + ".lock"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
PFX = "fgc"
ORG = "Ferrocarrils de la Generalitat de Catalunya (FGC)"
ODS_FILE = "https://dadesobertes.fgc.cat/api/datasets/1.0/webcams-actives-tim/files/{fid}"
IMAGE_MAGIC = (b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"\x89PNG\r\n\x1a\n")


def curl_bytes(url, timeout=30):
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        p = subprocess.run(
            ["curl", "-sL", "-A", UA, "--max-time", str(timeout), "-o", tmp, "-w", "%{http_code}|%{content_type}", url],
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


def is_image(body):
    return len(body) > 3000 and any(body[: len(m)] == m for m in IMAGE_MAGIC)


def resolve_image(entry):
    url = entry["url"]
    notes = []
    live_url = None
    if "roundshot.com" in url:
        code, _, body = curl_bytes(url, 25)
        if code == 200:
            m = re.search(rb'property="og:image"\s+content="([^"]+)"', body)
            if m:
                og = m.group(1).decode("utf-8", "replace")
                cand = urllib.parse.urljoin(url, og)
                c2, _, b2 = curl_bytes(cand, 25)
                if c2 == 200 and is_image(b2):
                    live_url = cand
                    notes.append("roundshot-og-image")
    if live_url is None:
        code, _, body = curl_bytes(url, 30)
        if code == 200 and is_image(body):
            live_url = url
    if live_url is None and entry.get("imatge_2_id"):
        cand = ODS_FILE.format(fid=entry["imatge_2_id"])
        code, _, body = curl_bytes(cand, 30)
        if code == 200 and is_image(body):
            live_url = cand
            notes.append("ods-file-fallback@2026-10-18")
    return live_url, notes


def main():
    if os.path.exists(LOCK):
        raise SystemExit("lock exists: " + LOCK)
    lock_fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(lock_fd)
    try:
        cat = json.load(open(CAT, encoding="utf-8"))
        assert len(cat) == 30, len(cat)
        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        existing = set()
        for r in rows:
            u = (r.get("live_stream_url") or "") + " " + (r.get("url") or "")
            for h in ("projecte4estacions", "pirineu365", "fgc.roundshot.com", "turismefgc", "cam=15100"):
                if h in u:
                    existing.add((r["csv_id"], u.strip()[:80]))
        assert not existing, f"overlap: {list(existing)[:5]}"

        next_idx = max(int(r["idx"]) for r in rows) + 1
        new_rows = []
        results = []
        for e in sorted(cat, key=lambda x: int(x["id"])):
            live_url, extra_notes = resolve_image(e)
            name = f'{e["name_bu"]} - {e["nom_servei"]}'
            notes = [
                f'fgc-webcam-id={e["id"]}',
                f'fgc-tipus={e["tipus_servei"]}',
                f'fgc-bu-id={e["business_unit"]}',
                "src=dadesobertes.fgc.cat:webcams-actives-tim",
                "lm=2026-10-18",
            ]
            if e.get("is_active") == 1:
                notes.append("ods-is-active=1")
            if live_url and live_url != e["url"]:
                notes.append(f'fgc-page={e["url"]}')
            notes.extend(extra_notes)
            if not live_url:
                notes.append("probe-failed@2026-10-18")
                if "webtv.feratel.com" in (e["url"] or ""):
                    notes.append("feratel-cam-retired-404@2026-10-18")
            if e["lat"] is None or e["lon"] is None:
                notes.append("location-unknown@2026-10-18")
            idx = next_idx
            cid = f"{PFX}_{idx:04d}"
            row = {k: "" for k in fieldnames}
            row["idx"] = str(idx)
            row["csv_id"] = cid
            row["project_name"] = name
            row["url"] = e["url"]
            row["live_stream_url"] = live_url or e["url"]
            row["type"] = "image"
            row["enabled"] = "True"
            row["live_status"] = "live" if live_url else ""
            if live_url:
                code, ctype, _ = curl_bytes(live_url, 20)
                row["http_status"] = str(code)
                row["content_type"] = (ctype or "").split(";")[0].strip()
            row["description"] = e["nom_servei"] or ""
            row["category"] = "scenic"
            row["likely_subject"] = "Mountain ski-resort webcam view (FGC)"
            row["country"] = "Spain"
            row["region"] = "Catalunya"
            row["city"] = e["name_bu"] or ""
            row["location_precision"] = "precise" if e["lat"] is not None else ""
            row["lat"] = f'{e["lat"]:.7f}'.rstrip("0").rstrip(".") if e["lat"] is not None else ""
            row["lon"] = f'{e["lon"]:.7f}'.rstrip("0").rstrip(".") if e["lon"] is not None else ""
            row["geo_source"] = "src=fgc-ods" if e["lat"] is not None else ""
            row["org"] = ORG
            row["host"] = urllib.parse.urlparse(row["live_stream_url"]).netloc
            row["confidence"] = "high"
            row["notes"] = "; ".join(notes)
            row["visibility"] = ""
            new_rows.append(row)
            results.append((cid, e["name_bu"], bool(live_url)))
            next_idx += 1

        posters = 0
        poster_fail = []
        os.makedirs(POSTER_DIR, exist_ok=True)
        for row in new_rows:
            if row["live_status"] != "live":
                continue
            code, _, body = curl_bytes(row["live_stream_url"], 30)
            if not (code == 200 and is_image(body)):
                poster_fail.append((row["csv_id"], f"code={code}"))
                continue
            try:
                img = Image.open(io.BytesIO(body))
                img.load()
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(os.path.join(POSTER_DIR, f'{row["idx"]}.jpg'), "JPEG", quality=80)
                posters += 1
            except Exception as ex:
                poster_fail.append((row["csv_id"], str(ex)[:60]))

        rows.extend(new_rows)
        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV)

        state = {
            "date": "2026-10-18",
            "source": "dadesobertes.fgc.cat/webcams-actives-tim (ODS records/1.0)",
            "ingested": len(new_rows),
            "live": sum(1 for _, _, l in results if l),
            "dead": [c for c, _, l in results if not l],
            "posters": posters,
            "poster_fail": poster_fail,
            "rows_after": len(rows),
            "idx_range": [int(new_rows[0]["idx"]), int(new_rows[-1]["idx"])],
        }
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print(f"[fgc] rows={len(new_rows)} live={state['live']} dead={state['dead']} posters={posters} total={len(rows)}")
        for c, bu, l in results:
            print(f"  {c} {bu} {'live' if l else 'DEAD'}")
        if poster_fail:
            print("poster_fail:", poster_fail)
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
