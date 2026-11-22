# -*- coding: utf-8 -*-
"""Session 51: ingest missing Richmond BC traffic cams.

- 6 site-referenced cams absent from the CSV (new/renamed on IntersectionDetails pages)
- 13 unreferenced-but-live cams found via Wayback CDX diff (unique content; the
  18-file 76,480-byte group is a shared 'camera unavailable' placeholder and is skipped)
"""
import csv
import json
import os
import re
import ssl
import urllib.request

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
LOCK = CSV + ".lock"
STATE = os.path.join(ROOT, "camera_testing", "_richmond", "richmond_ingest_state.json")
SITE_JSON = os.path.join(ROOT, "camera_testing", "_richmond", "richmond_cams.json")
HIDDEN_JSON = os.path.join(ROOT, "camera_testing", "_richmond", "richmond_hidden_live.json")
WAYBACK_JSON = r"C:\Users\eli6-admin\AppData\Local\Temp\opencode\_rich_wayback_hits.json"

DESC = ("Traffic-camera still from the City of Richmond traffic camera map (TICS); "
        "image refreshes about every 1 minute.")
DIRNAME = {'nb': 'NB', 'sb': 'SB', 'eb': 'EB', 'wb': 'WB',
           'northbound': 'NB', 'southbound': 'SB', 'eastbound': 'EB', 'westbound': 'WB',
           'northeast': 'NE', 'northwest': 'NW', 'southeast': 'SE', 'southwest': 'SW'}

UA = {'User-Agent': 'Mozilla/5.0'}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def head(url):
    try:
        req = urllib.request.Request(url, headers=UA, method='HEAD')
        with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
            return r.status, r.headers.get('Content-Type', ''), r.headers.get('Last-Modified', '')
    except Exception as e:
        return 0, '', str(e)[:60]


def dir_from_alt(alt):
    m = re.search(r'\b(northbound|southbound|eastbound|westbound|northeast|northwest|southeast|southwest)\s*$',
                  alt or '', re.I)
    if m:
        return DIRNAME[m.group(1).lower()]
    m = re.search(r'\s(\w{2})$', alt or '')
    return DIRNAME.get(m.group(1).lower(), '') if m else ''


def dir_from_file(fn):
    stem = fn.rsplit('.', 1)[0]
    m = re.search(r'_(nb|sb|eb|wb)(\d*)$', stem, re.I)
    return DIRNAME[m.group(1).lower()] + m.group(2) if m else ''


def row_for(fieldnames, idx, iid, name, fn, direction, lat, lon, extra_notes):
    url = "https://www.richmond.ca/trafficcam/" + fn
    code, ctype, lm = head(url)
    r = {f: "" for f in fieldnames}
    label = ("%s %s Richmond, BC" % (name, direction)).replace("  ", " ")
    r.update({
        "idx": str(idx),
        "project_name": label,
        "url": url,
        "live_stream_url": url,
        "type": "image",
        "enabled": "True",
        "live_status": "live" if code == 200 else "",
        "http_status": str(code) if code else "",
        "content_type": ctype or "",
        "server_header": "Microsoft-IIS/10.0",
        "page_title": "City of Richmond Traffic Cameras",
        "description": DESC,
        "category": "traffic",
        "likely_subject": "Roadway traffic at %s%s" % (
            name, ", %s approach" % direction if direction else ""),
        "country": "Canada",
        "region": "British Columbia",
        "city": "Richmond",
        "address": name,
        "road": name,
        "location_precision": "intersection_marker" if lat else "",
        "lat": lat,
        "lon": lon,
        "geo_source": "richmond.ca:trafficcameras-map" if lat else "",
        "org": "City of Richmond",
        "host": "www.richmond.ca",
        "confidence": "high" if code == 200 else "medium",
        "notes": ("Family=richmond-tics, kind=jpeg-still, weight=30, "
                  "source=richmond.ca-trafficcameras, cam_id=%s, refresh=~1min, "
                  "delivery=static-jpg (no public live video; TICS internal)%s" % (
                      fn.rsplit('.', 1)[0], extra_notes)),
        "csv_id": "ric_%d" % idx,
        "visibility": "",
    })
    if iid:
        r["notes"] += ", intersection_id=%s" % iid
    return r


def main():
    site = json.load(open(SITE_JSON, encoding="utf-8"))
    hidden = json.load(open(HIDDEN_JSON, encoding="utf-8"))
    wb = {}
    if os.path.exists(WAYBACK_JSON):
        try:
            wb = json.load(open(WAYBACK_JSON, encoding="utf-8"))
        except Exception:
            wb = {}

    site_by_iid = {it["id"]: it for it in site}
    site_cams = {}
    for it in site:
        for c in it.get("cams", []):
            site_cams[c["url"].split("/")[-1].lower()] = (it, c)

    if os.path.exists(LOCK):
        raise SystemExit("lock exists: " + LOCK)
    os.close(os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    try:
        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        existing = set()
        for r in rows:
            for k in ("url", "live_stream_url"):
                u = (r.get(k) or "").strip()
                if u:
                    existing.add(u.split("/")[-1].lower())
        next_idx = max(int(r["idx"]) for r in rows) + 1

        new_rows = []

        # 1) site-referenced cams missing from the CSV
        for it in site:
            for c in it.get("cams", []):
                fn = c["url"].split("/")[-1]
                if fn.lower() in existing:
                    continue
                direction = dir_from_alt(c.get("alt", "")) or dir_from_file(fn)
                r = row_for(fieldnames, next_idx, it["id"], it["name"], fn, direction,
                            "%.8f" % it["lat"], "%.8f" % it["lon"], "")
                new_rows.append(r)
                existing.add(fn.lower())
                next_idx += 1

        # 2) hidden unreferenced-but-live cams
        for h in hidden:
            fn = h["file"]
            if fn.lower() in existing:
                continue
            stem = fn.rsplit(".", 1)[0]
            iid, name, direction, lat, lon, extra = "", "", "", "", "", ""
            serial = ""
            m = re.match(r"^([0-9A-Fa-f]{16})_(\d+)\.jpg$", fn)
            if m:
                serial = m.group(1).upper()
                hit = wb.get(serial) or {}
                if hit:
                    iid = hit.get("id", "")
                    direction = hit.get("direction", "")
                    name = hit.get("title", "") or serial
                    it = site_by_iid.get(iid)
                    if it:
                        name = it["name"]
                        lat, lon = "%.8f" % it["lat"], "%.8f" % it["lon"]
                    extra = ", legacy-serial, unreferenced-live (wayback page %s), serial=%s" % (iid, serial)
                else:
                    name = "Richmond BC camera %s" % serial
                    extra = ", unreferenced-live (wayback-only filename), serial=%s" % serial
            elif fn.lower().startswith("vdd_"):
                # vdd_<road>_<road2|block>_<dir>.jpg
                direction = dir_from_file(fn)
                if "aberdeen_cambie" in fn.lower():
                    iid, it = "3402", site_by_iid.get("3402")
                    name = it["name"] if it else "8100 block at Cambie Road"
                elif "st._edwards_bridgeport" in fn.lower():
                    iid, it = "4450", site_by_iid.get("4450")
                    name = it["name"] if it else "St. Edwards Drive at Bridgeport Road"
                elif "no_3_5300" in fn.lower():
                    iid = "3340"
                    name = "No. 3 Road at 5300 block"
                    for rr in rows:
                        if rr.get("live_stream_url", "").endswith("vdd_no_3_5300_sb.jpg"):
                            lat, lon = rr.get("lat", ""), rr.get("lon", "")
                            break
                else:
                    name = stem
                if iid and site_by_iid.get(iid):
                    it = site_by_iid[iid]
                    lat, lon = "%.8f" % it["lat"], "%.8f" % it["lon"]
                extra = ", legacy filename, unreferenced-live (wayback-only)"
            else:
                name = stem
                extra = ", unreferenced-live"

            r = row_for(fieldnames, next_idx, iid, name, fn, direction, lat, lon, extra)
            new_rows.append(r)
            existing.add(fn.lower())
            next_idx += 1

        if os.environ.get("DRY"):
            print("[richmond] DRY RUN: would ingest %d rows" % len(new_rows))
            for r in new_rows:
                print("  %-12s %-52s %-40s lat=%s lon=%s" % (
                    r["csv_id"], r["project_name"][:52],
                    r["live_stream_url"].split("/")[-1], r["lat"], r["lon"]))
            return

        rows.extend(new_rows)
        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV)

        json.dump({"rows_after": len(rows), "ingested": [r["csv_id"] for r in new_rows],
                   "count": len(new_rows)},
                  open(STATE, "w", encoding="utf-8"), indent=1)

        print("[richmond] ingested=%d total=%d" % (len(new_rows), len(rows)))
        for r in new_rows:
            print("  %-12s %-52s %-40s live=%r" % (
                r["csv_id"], r["project_name"][:52], r["live_stream_url"].split("/")[-1],
                r["live_status"]))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
