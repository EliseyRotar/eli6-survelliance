# -*- coding: utf-8 -*-
"""Session 47o: ingest 12 new eTraffic-registered DGT cams (image 404,
pipeline lag) + stamp still-dead notes on 22 prior-dead rows."""
import csv
import json
import os

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "es_dgt_recensus_state.json")
LOCK = CSV + ".lock"
DATE = "2026-10-19"
SUBJ = "Live public camera"

rec = json.load(open(os.path.join(ROOT, "camera_testing",
                                  "_es_recensus_%s.json" % DATE), encoding="utf-8"))
prod = json.load(open(os.path.join(ROOT, "camera_testing",
                                   "_es_camaras_etraffic_%s.json" % DATE), encoding="utf-8"))["cams"]
by_id = {c["idCamara"]: c for c in prod}
new_live = {k for k, v in rec["new"].items() if v["live"]}

if os.path.exists(LOCK):
    raise SystemExit("lock exists: " + LOCK)
os.close(os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
try:
    with open(CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    existing = {x for r in rows for x in (r.get("url"), r.get("live_stream_url")) if x}

    # stamp still-dead rows
    stamped = 0
    for r in rows:
        if "image-404@2026-10-17" in (r.get("notes") or "") and \
                "still-404@%s" % DATE not in (r.get("notes") or ""):
            r["notes"] = (r.get("notes") or "") + "; still-404@%s" % DATE
            stamped += 1

    next_idx = max(int(x["idx"]) for x in rows) + 1
    new_rows = []
    for cid in sorted(rec["new"], key=int):
        url = "https://etraffic.dgt.es/camarasEtraffic/%s.jpg" % cid
        if url in existing:
            continue
        meta = by_id.get(cid, {})
        road = meta.get("carretera", "")
        pk = meta.get("pk", "")
        idx = next_idx
        row = {f: "" for f in fieldnames}
        row.update({
            "idx": str(idx),
            "csv_id": "dgt_%d" % idx,
            "project_name": "%s km %s -" % (road, pk),
            "url": url,
            "live_stream_url": url,
            "type": "image",
            "enabled": "True",
            "live_status": "live" if cid in new_live else "",
            "http_status": str(rec["new"][cid]["code"]),
            "content_type": rec["new"][cid].get("ctype", ""),
            "description": "DGT eTraffic %s km %s (sentido %s)" % (road, pk, meta.get("sentido", "")),
            "category": "traffic",
            "likely_subject": SUBJ,
            "country": "Spain",
            "region": "Pontevedra",
            "city": "",
            "lat": str(meta.get("coordY", "")),
            "lon": str(meta.get("coordX", "")),
            "location_precision": "precise",
            "geo_source": "host:etraffic.dgt.es",
            "org": "DGT",
            "host": "etraffic.dgt.es",
            "confidence": "high",
            "notes": ("etraffic-api-registered@%s; image-404 (registered in getCamaras but "
                      "camarasEtraffic host not yet serving - pipeline lag or pre-commission); "
                      "recheck@next-session" % DATE),
            "visibility": "",
        })
        new_rows.append(row)
        next_idx += 1

    rows.extend(new_rows)
    tmp = CSV + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CSV)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"date": DATE, "phase": "done", "still_dead_stamped": stamped,
                   "ingested": [r["csv_id"] for r in new_rows],
                   "rows_after": len(rows)}, f, ensure_ascii=False, indent=1)
    print("[dgt-recensus] stamped=%d ingested=%d total=%d" % (
        stamped, len(new_rows), len(rows)))
    for r in new_rows:
        print("  %s %s live=%r" % (r["csv_id"], r["project_name"], r["live_status"]))
finally:
    try:
        os.remove(LOCK)
    except OSError:
        pass
