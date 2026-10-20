# -*- coding: utf-8 -*-
"""Session 48i: IEM (mesonet.agron.iastate.edu) archive loops for 13 cams.

Per cam: download last 7 days of 5-min frames (archive/data/YYYY/MM/DD/camera/
CAM/CAM_YYYYMMDDHHMM.jpg) -> archive_7d.mp4 (4 fps) + archive_1d.gif from the
last day (6 fps, 640px). Incremental: existing frames reused; frames deleted
after encode to save disk.
"""
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT = os.path.join(ROOT, "web_viewer", "static", "loops", "iem")
TEMP = os.environ["TEMP"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
CAMS = ["KCCI-027", "KCCI-034", "KCCI-036", "KCRG-001", "KCRG-005", "KCRG-012",
        "KCRG-013", "KCRG-016", "KCRG-018", "KCRG-027", "KCRG-029", "KCRG-032", "KCRG-035"]
DAYS = 7


def day_list(end: date, n: int):
    return [end - timedelta(days=i) for i in range(n - 1, -1, -1)]


def list_day(cam, d):
    url = "https://mesonet.agron.iastate.edu/archive/data/%04d/%02d/%02d/camera/%s/" % (
        d.year, d.month, d.day, cam)
    p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", "40", url],
                       capture_output=True, timeout=50)
    text = p.stdout.decode("utf-8", "replace")
    return re.findall(r'href=["\'](%s_\d{12}\.jpg)["\']' % re.escape(cam), text)


def fetch_file(url, out):
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return True
    p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", "40", "-o", out,
                        "-w", "%{http_code}", url],
                       capture_output=True, text=True, timeout=50)
    if (p.stdout or "").strip() == "200" and os.path.exists(out):
        with open(out, "rb") as f:
            if f.read(2) == b"\xff\xd8":
                return True
    if os.path.exists(out):
        try:
            os.remove(out)
        except OSError:
            pass
    return False


def build_cam(cam):
    d = os.path.join(OUT, cam)
    fdir = os.path.join(d, "frames")
    os.makedirs(fdir, exist_ok=True)
    mp4 = os.path.join(d, "archive_7d.mp4")
    gif = os.path.join(d, "archive_1d.gif")
    marker = os.path.join(d, "build_done.json")
    if os.path.exists(marker) and os.path.exists(mp4) and os.path.exists(gif):
        n = len(os.listdir(fdir))
        return cam, "ok(cached)", n
    today = date.today()
    files = sorted(os.listdir(fdir))
    if len(files) < 200:  # not yet populated
        names = []
        for dd in day_list(today, DAYS):
            try:
                names += list_day(cam, dd)
            except Exception as e:
                print("  %s list fail %s %s" % (cam, dd, e), flush=True)
            time.sleep(0.2)
        names = sorted(set(names))
        base = os.path.join(fdir, "raw")
        os.makedirs(base, exist_ok=True)

        def dl2(name):
            stamp = name[len(cam) + 1:len(cam) + 13]
            y, mo, dy = stamp[0:4], stamp[4:6], stamp[6:8]
            url = "https://mesonet.agron.iastate.edu/archive/data/%s/%s/%s/camera/%s/%s" % (
                y, mo, dy, cam, name)
            return fetch_file(url, os.path.join(base, name))
        ok = 0
        with ThreadPoolExecutor(max_workers=4) as ex:
            for r in ex.map(dl2, names):
                ok += 1 if r else 0
        # sequential rename by timestamp order
        raw = sorted(f for f in os.listdir(base) if f.endswith(".jpg"))
        for i, f in enumerate(raw):
            os.replace(os.path.join(base, f), os.path.join(fdir, "%05d.jpg" % i))
        try:
            os.rmdir(base)
        except OSError:
            pass
        files = sorted(f for f in os.listdir(fdir) if f.endswith(".jpg"))
    n = len(files)
    if n < 10:
        return cam, "skip(%d)" % n, n
    p1 = subprocess.run(["ffmpeg", "-y", "-framerate", "4", "-i", os.path.join(fdir, "%05d.jpg"),
                         "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                         mp4], capture_output=True, timeout=600)
    # gif from last 288 frames (1 day) if available
    gif_start = max(0, n - 288)
    p2 = subprocess.run(
        ["ffmpeg", "-y", "-start_number", str(gif_start), "-framerate", "6",
         "-i", os.path.join(fdir, "%05d.jpg"),
         "-vf", "fps=6,scale=480:-2:flags=lanczos,split[s0][s1];"
                "[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
         gif], capture_output=True, timeout=600)
    ok1 = p1.returncode == 0 and os.path.exists(mp4)
    ok2 = p2.returncode == 0 and os.path.exists(gif)
    # delete frames to save disk once built
    if ok1 and ok2:
        with open(marker, "w") as fh:
            json.dump({"frames": n, "mp4_bytes": os.path.getsize(mp4),
                       "gif_bytes": os.path.getsize(gif)}, fh)
        for f in files:
            try:
                os.remove(os.path.join(fdir, f))
            except OSError:
                pass
    return cam, ("ok" if ok1 and ok2 else "mp4=%s gif=%s" % (ok1, ok2)), n


def main():
    os.makedirs(OUT, exist_ok=True)
    res = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(build_cam, c): c for c in CAMS}
        for f in as_completed(futs):
            cam, status, n = f.result()
            res[cam] = [status, n]
            print("%-10s %-14s frames=%d" % (cam, status, n), flush=True)
    ok = sum(1 for v in res.values() if v[0].startswith("ok"))
    print("\nIEM SUMMARY ok=%d/%d" % (ok, len(CAMS)))
    json.dump(res, open(os.path.join(ROOT, "camera_testing", "iem_loops.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
