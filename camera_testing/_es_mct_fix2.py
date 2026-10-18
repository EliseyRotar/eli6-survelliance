# -*- coding: utf-8 -*-
"""Session 47d(2) - repair mct image URLs.

RenderService?sctidcam= 302-redirects to http:// (unusable over https).
Canonical working endpoint: https://mct.gencat.cat/mct2bo/TransitCamera?nom=X&visualitzacio=imatge
- 123 probe-failed rows: switch URL to TransitCamera, re-probe, posters
- Terrassa rows (emap origin, live): update mct-alt note to TransitCamera form
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
STATE = os.path.join(ROOT, "camera_testing", "_es_mct_fix2_state.json")
POSTER_DIR = os.path.join(ROOT, "web_viewer", "static", "posters")
LOCK = CSV + ".lock"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) eli6-surveillance-research/1.0"
TC = "https://mct.gencat.cat/mct2bo/TransitCamera?nom={n}&visualitzacio=imatge"


def http_get(url, timeout=18):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()


def main():
    if os.path.exists(LOCK):
        raise SystemExit("lock exists: " + LOCK)
    os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        to_probe = {}
        alt_fixed = 0
        for r in rows:
            notes = r.get("notes") or ""
            if "mct-id=" not in notes:
                continue
            m = re.search(r"mct-id=([^;]+)", notes)
            mid = m.group(1).strip()
            tc = TC.format(n=mid)
            if "emap.terrassa.cat" in (r.get("live_stream_url") or ""):
                notes2 = re.sub(r"mct-alt=\S+", "mct-alt=" + tc, notes)
                if notes2 != notes:
                    r["notes"] = notes2
                    alt_fixed += 1
                continue
            if "probe-failed@2026-10-17" in notes:
                r["notes"] = notes.replace("; probe-failed@2026-10-17", "").strip("; ")
            r["live_stream_url"] = tc
            r["live_status"] = ""
            to_probe[r["idx"]] = r

        print(f"to_probe={len(to_probe)} alt_fixed={alt_fixed}")
        live, dead = [], []
        posters, poster_fail = 0, []
        os.makedirs(POSTER_DIR, exist_ok=True)
        for idx, r in to_probe.items():
            url = r["live_stream_url"]
            data = None
            for attempt in range(2):
                try:
                    status, ctype, body = http_get(url)
                    if status == 200 and len(body) > 3000 and (
                        body[:3] == b"\xff\xd8\xff"
                        or body[:6] in (b"GIF87a", b"GIF89a")
                        or body[:8] == b"\x89PNG\r\n\x1a\n"
                    ):
                        data = body
                        break
                except Exception:
                    time.sleep(1.2)
            if data:
                r["live_status"] = "live"
                live.append(r["csv_id"])
                cache = os.path.join(ROOT, "camera_testing", "_es_cache", f"mct2_{r['csv_id']}.bin")
                os.makedirs(os.path.dirname(cache), exist_ok=True)
                with open(cache, "wb") as cf:
                    cf.write(data)
                try:
                    img = Image.open(io.BytesIO(data))
                    img.load()
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(os.path.join(POSTER_DIR, f"{idx}.jpg"), "JPEG", quality=80)
                    posters += 1
                except Exception as e:
                    poster_fail.append((r["csv_id"], str(e)[:80]))
            else:
                r["notes"] = (r.get("notes") or "") + "; probe-failed2@2026-10-17"
                dead.append(r["csv_id"])

        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV)

        state = {
            "date": "2026-10-17",
            "to_probe": len(to_probe),
            "alt_fixed": alt_fixed,
            "live": len(live),
            "dead": dead,
            "posters": posters,
            "poster_fail": poster_fail,
        }
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print(f"[mct2] live={len(live)} dead={len(dead)} posters={posters} dead_ids={dead[:10]}")
        if poster_fail:
            print("poster_fail:", poster_fail[:5])
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
