# -*- coding: utf-8 -*-
"""Session 48a: Calgary ingest + rectification.

1. Rectify junk-named trafficcam.calgary.ca rows (argus 'Canada ·
   Trafficcam · #' pattern) from official Socrata k7p9-kppz
   (camera_location, quadrant, GeoJSON point).  Unlisted loc ids
   (10,109,118,171) get cleaned generic names + region/city only.
2. Ingest 4 live-but-unlisted cams missing from CSV:
   loc159, loc169, loc210, loc223 (prefix yyc_).
"""
import csv
import json
import os
import re
import subprocess
import tempfile

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "yyc_ingest_state.json")
LOCK = CSV + ".lock"
TEMP = os.environ["TEMP"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DATE = "2026-10-19"
SUBJ = "Live public camera"

MISSING = [159, 169, 210, 223]


def get_meta(url, timeout=18, out="ing.bin"):
    op = os.path.join(TEMP, out)
    p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", str(timeout),
                        "-o", op, "-w", "%{http_code}|%{content_type}", url],
                       capture_output=True, text=True, timeout=timeout + 8)
    meta = (p.stdout or "").strip().split("|")
    code = int(meta[0]) if meta and meta[0].isdigit() else 0
    ctype = meta[1] if len(meta) > 1 else ""
    head = b""
    if os.path.exists(op):
        with open(op, "rb") as f:
            head = f.read(2)
    return code, ctype, head


def main():
    if os.path.exists(LOCK):
        raise SystemExit("lock exists")
    os.close(os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    try:
        socr = json.load(open(os.path.join(TEMP, "k7p9-kppz.json"), encoding="utf-8"))
        by_loc = {}
        for c in socr:
            u = (c.get("camera_url") or {}).get("url", "")
            m = re.search(r"loc(\d+)\.jpg", u)
            if m:
                by_loc[int(m.group(1))] = c

        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        existing_urls = {x for r in rows for x in (r.get("url"), r.get("live_stream_url")) if x}
        existing_locs = set()
        for r in rows:
            m = re.search(r"loc(\d+)\.jpg",
                          (r.get("live_stream_url") or "") + (r.get("url") or ""))
            if m and "trafficcam.calgary.ca" in ((r.get("live_stream_url") or "") + (r.get("url") or "")):
                existing_locs.add(int(m.group(1)))

        # ---- rectify junk rows ----
        rectified = 0
        unlisted_cleaned = 0
        for r in rows:
            u_combo = (r.get("live_stream_url") or "") + "|" + (r.get("url") or "")
            if "trafficcam.calgary.ca" not in u_combo:
                continue
            name = r.get("project_name") or ""
            if " · " not in name and not name.startswith("Canada"):
                continue  # good rows untouched
            m = re.search(r"loc(\d+)\.jpg", u_combo)
            loc = int(m.group(1)) if m else None
            off = by_loc.get(loc) if loc is not None else None
            if off:
                loc_name = off.get("camera_location", "")
                quad = off.get("quadrant", "")
                pt = (off.get("point") or {}).get("coordinates", [None, None])
                lon, lat = (pt + [None, None])[:2] if pt else (None, None)
                r["project_name"] = "%s (%s)" % (loc_name, quad) if quad else loc_name
                if lat is not None:
                    r["lat"] = str(lat)
                    r["lon"] = str(lon)
                    r["location_precision"] = "precise"
                    r["geo_source"] = "opendata:calgary:k7p9-kppz"
                r["region"] = "Alberta"
                r["city"] = "Calgary"
                r["category"] = "traffic"
                r["likely_subject"] = SUBJ
                r["org"] = "City of Calgary"
                r["host"] = "trafficcam.calgary.ca"
                r["type"] = "image"
                notes = r.get("notes") or ""
                add = ("rectified-2026-10-19-from-official-source; loc=%d; "
                       "opendata=k7p9-kppz" % loc)
                r["notes"] = (notes + "; " + add) if notes else add
                rectified += 1
            else:
                # unlisted (10,109,118,171): cleaned generic name
                if loc is not None:
                    r["project_name"] = "Calgary traffic camera (unlisted loc%d)" % loc
                r["region"] = "Alberta"
                r["city"] = "Calgary"
                r["category"] = "traffic"
                r["host"] = "trafficcam.calgary.ca"
                notes = r.get("notes") or ""
                add = ("unlisted-on-opendata; cleaned-2026-10-19; loc=%s" % (loc,))
                r["notes"] = (notes + "; " + add) if notes else add
                unlisted_cleaned += 1

        # ---- ingest 4 missing ----
        next_idx = max(int(x["idx"]) for x in rows) + 1
        new_rows = []
        results = []
        for loc in MISSING:
            url = "https://trafficcam.calgary.ca/loc%d.jpg" % loc
            if url in existing_urls or loc in existing_locs:
                results.append((loc, "skip"))
                continue
            code, ctype, head = get_meta(url)
            live = code == 200 and (head[:2] == b"\xff\xd8" or "image" in ctype)
            idx = next_idx
            row = {f: "" for f in fieldnames}
            row.update({
                "idx": str(idx),
                "csv_id": "yyc_%d" % idx,
                "project_name": "Calgary traffic camera (unlisted loc%d)" % loc,
                "url": url,
                "live_stream_url": url,
                "type": "image",
                "enabled": "True",
                "live_status": "live" if live else "",
                "http_status": str(code),
                "content_type": ctype,
                "description": "City of Calgary traffic camera loc%d (not in open-data k7p9-kppz)" % loc,
                "category": "traffic",
                "likely_subject": SUBJ,
                "country": "Canada",
                "region": "Alberta",
                "city": "Calgary",
                "lat": "",
                "lon": "",
                "location_precision": "no_geocode_result",
                "geo_source": "",
                "org": "City of Calgary",
                "host": "trafficcam.calgary.ca",
                "confidence": "high",
                "notes": ("unlisted-on-opendata (absent k7p9-kppz); image-live-verified@%s; "
                          "no public coords" % DATE),
                "visibility": "",
            })
            new_rows.append(row)
            results.append((loc, "live" if live else "DEAD %s" % code))
            next_idx += 1

        rows.extend(new_rows)
        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV)
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump({"date": DATE, "phase": "done",
                       "rectified_official": rectified,
                       "unlisted_cleaned": unlisted_cleaned,
                       "ingested": [r["csv_id"] for r in new_rows],
                       "rows_after": len(rows)}, f, ensure_ascii=False, indent=1)
        print("[yyc] rectified_official=%d unlisted_cleaned=%d ingested=%d total=%d" % (
            rectified, unlisted_cleaned, len(new_rows), len(rows)))
        for loc, s in results:
            print("  loc%-4d %s" % (loc, s))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
