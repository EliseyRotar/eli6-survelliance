import csv
import json
import os
import re
import subprocess
import tempfile

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "es_cuenca_torv_state.json")
LOCK = CSV + ".lock"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DATE = "2026-10-19"
SUBJ = "Live public camera"

CAMS = [
    # -- Cuenca (Ayuntamiento) --
    {"prefix": "cuen", "name": "Cuenca - Plaza Mayor",
     "url": "https://webcam.cuenca.es/live_plazamayor/readImage.asp", "kind": "img",
     "desc": "Webcam Ayuntamiento de Cuenca, Plaza Mayor (fija urbana)",
     "region": "Castilla-La Mancha", "city": "Cuenca",
     "lat": "40.0687", "lon": "-2.1345", "org": "Ayuntamiento de Cuenca",
     "host": "webcam.cuenca.es", "cat": "city",
     "notes": "src=cuenca.es:webcam-plaza-mayor; axis-asp=readImage.asp; live-checked@%s" % DATE},
    {"prefix": "cuen", "name": "Cuenca - San Miguel (Anteplaza)",
     "url": "https://cuenca.es/webcam/image.jpg", "kind": "img",
     "desc": "Webcam Excmo. Ayto. Cuenca - Anteplaza (junto a Iglesia de San Miguel)",
     "region": "Castilla-La Mancha", "city": "Cuenca",
     "lat": "40.0693", "lon": "-2.1317", "org": "Ayuntamiento de Cuenca",
     "host": "cuenca.es", "cat": "city",
     "notes": "src=cuenca.es:webcam-sanmiguel; embed=imagen.php->image-r.jpg (960x540, title 'Anteplaza'); "
              "full-res=image.jpg (1920x1080, same Last-Modified=same cam); live-checked@%s" % DATE},
    # -- Torrevieja (Proyecto Mastral) --
    {"prefix": "trv", "name": "Torrevieja - Laguna (Hospital Universitario)",
     "url": "https://www.youtube.com/watch?v=SxXx0nFpJRo", "kind": "yt", "yt": "SxXx0nFpJRo",
     "desc": "Laguna de Torrevieja. Hospital Universitario. Webcam de Torrevieja (Proyecto Mastral)",
     "region": "Comunidad Valenciana", "city": "Torrevieja",
     "lat": "37.9700", "lon": "-0.6800", "org": "Proyecto Mastral",
     "host": "www.youtube.com", "cat": "nature",
     "notes": "src=eltiempoentorrevieja.es:webcams; channel=ProyectoMastral; live-checked@%s; yt-id=%s"
              % (DATE, "SxXx0nFpJRo")},
    {"prefix": "trv", "name": "Torrevieja - Salinas (nueva emisión)",
     "url": "https://www.youtube.com/watch?v=kyWsLIVS4Oo", "kind": "yt", "yt": "kyWsLIVS4Oo",
     "desc": "Salinas de Torrevieja - Webcam en directo (Proyecto Mastral, id actual en portal webcams)",
     "region": "Comunidad Valenciana", "city": "Torrevieja",
     "lat": "37.9800", "lon": "-0.6500", "org": "Proyecto Mastral",
     "host": "www.youtube.com", "cat": "nature",
     "notes": "src=eltiempoentorrevieja.es:webcams; channel=ProyectoMastral; "
              "tv_133987 p3m2po8KcAg = emisión salinas anterior (ambas live); live-checked@%s; yt-id=%s"
              % (DATE, "kyWsLIVS4Oo")},
    {"prefix": "trv", "name": "Torrevieja - Laguna de La Mata",
     "url": "https://www.youtube.com/watch?v=pKAlUXmJnDU", "kind": "yt", "yt": "pKAlUXmJnDU",
     "desc": "Laguna de La Mata - Parque Natural Lagunas de La Mata y Torrevieja (Proyecto Mastral)",
     "region": "Comunidad Valenciana", "city": "Torrevieja",
     "lat": "38.0200", "lon": "-0.6500", "org": "Proyecto Mastral",
     "host": "www.youtube.com", "cat": "nature",
     "notes": "src=eltiempoentorrevieja.es:webcams; channel=ProyectoMastral; "
              "distinct from tv_133989 Playa de La Mata beach; live-checked@%s; yt-id=%s"
              % (DATE, "pKAlUXmJnDU")},
]


def curl(url, out=None, timeout=30):
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

        next_idx = max(int(x["idx"]) for x in rows) + 1
        new_rows, results = [], []
        for c in CAMS:
            if c["url"] in existing:
                results.append((c["name"], "skip"))
                continue
            code, ctype, body = curl(c["url"])
            if c["kind"] == "img":
                live = code == 200 and (ctype.startswith("image/") or body[:2] == b"\xff\xd8")
            else:
                html = body.decode("utf-8", "replace")
                live = code == 200 and (
                    '"isLive":true' in html or '"isLiveContent":true' in html)
            idx = next_idx
            row = {f: "" for f in fieldnames}
            row.update({
                "idx": str(idx),
                "csv_id": "%s_%d" % (c["prefix"], idx),
                "project_name": c["name"],
                "url": c["url"],
                "live_stream_url": c["url"],
                "type": "video" if c["kind"] == "yt" else "image",
                "enabled": "True",
                "live_status": "live" if live else "",
                "http_status": str(code) if code else "",
                "content_type": ctype,
                "description": c["desc"],
                "category": c["cat"],
                "likely_subject": SUBJ,
                "country": "Spain",
                "region": c["region"],
                "city": c["city"],
                "lat": c["lat"],
                "lon": c["lon"],
                "location_precision": "precise",
                "geo_source": "manual",
                "org": c["org"],
                "host": c["host"],
                "confidence": "high",
                "notes": c["notes"],
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
                 "ingested": [r["csv_id"] for r in new_rows],
                 "live": sum(1 for _, s in results if s == "live"),
                 "rows_after": len(rows)}
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print("[cuenca+torv] ingested=%d live=%d total=%d" % (
            len(new_rows), state["live"], len(rows)))
        for nm, s in results:
            print("  %-48s %s" % (nm, s))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
