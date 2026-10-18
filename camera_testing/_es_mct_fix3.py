# -*- coding: utf-8 -*-
"""Session 47d(3) - append .gif to TransitCamera nom= (nom_fitxer has no ext) + re-probe."""
import csv
import io
import json
import os
import re
import subprocess
import tempfile
import time

from PIL import Image

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "_es_mct_fix3_state.json")
POSTER_DIR = os.path.join(ROOT, "web_viewer", "static", "posters")
LOCK = CSV + ".lock"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) eli6-surveillance-research/1.0"
TC = "https://mct.gencat.cat/mct2bo/TransitCamera?nom={n}&visualitzacio=imatge"


def http_get(url, timeout=25):
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        p = subprocess.run(
            ["curl", "-s", "-A", UA, "--max-time", str(timeout), "-o", tmp, "-w", "%{http_code}", url],
            capture_output=True, text=True, timeout=timeout + 10,
        )
        code = (p.stdout or "").strip()
        with open(tmp, "rb") as f:
            body = f.read()
        return int(code or 0), "", body
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
        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        to_probe = {}
        for r in rows:
            notes = r.get("notes") or ""
            if "mct-id=" not in notes or "emap.terrassa.cat" in (r.get("live_stream_url") or ""):
                continue
            mid = re.search(r"mct-id=([^;]+)", notes).group(1).strip()
            if "." not in mid:
                mid += ".gif"
            tc = TC.format(n=mid)
            if tc == r.get("live_stream_url") and r.get("live_status") == "live":
                continue
            notes2 = notes
            for marker in ("; probe-failed@2026-10-17", "; probe-failed2@2026-10-17", "; probe-failed3@2026-10-17"):
                notes2 = notes2.replace(marker, "")
            r["notes"] = notes2.strip("; ")
            r["live_stream_url"] = tc
            r["live_status"] = ""
            to_probe[r["idx"]] = r

        print(f"to_probe={len(to_probe)}")
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
                cache = os.path.join(ROOT, "camera_testing", "_es_cache", f"mct3_{r['csv_id']}.bin")
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
                r["notes"] = (r.get("notes") or "") + "; probe-failed3@2026-10-17"
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
            "live": len(live),
            "dead": dead,
            "posters": posters,
            "poster_fail": poster_fail,
        }
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print(f"[mct3] live={len(live)} dead={len(dead)} posters={posters} dead_ids={dead[:10]}")
        if poster_fail:
            print("poster_fail:", poster_fail[:5])
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
