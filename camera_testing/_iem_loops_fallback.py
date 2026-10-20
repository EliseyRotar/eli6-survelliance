# -*- coding: utf-8 -*-
"""Session 48l: IEM fallback for retired cams (no recent 7-day dirs).

Walks back month-by-month (up to 30 months) to find the latest non-empty
archive day for cams whose last-7-day window is empty, then builds the same
archive_7d.mp4 + archive_1d.gif from that anchor window.
"""
import json
import os
import re
import subprocess
import time
from datetime import date, timedelta

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT = os.path.join(ROOT, "web_viewer", "static", "loops", "iem")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
STATE = os.path.join(ROOT, "camera_testing", "iem_loops.json")


def curl(url, out=None, timeout=40):
    args = ["curl", "-sL", "-A", UA, "--max-time", str(timeout)]
    if out:
        args += ["-o", out, "-w", "%{http_code}"]
    args.append(url)
    p = subprocess.run(args, capture_output=True, timeout=timeout + 10)
    return p.stdout


def day_names(cam, d):
    url = "https://mesonet.agron.iastate.edu/archive/data/%04d/%02d/%02d/camera/%s/" % (
        d.year, d.month, d.day, cam)
    try:
        text = curl(url).decode("utf-8", "replace")
    except Exception:
        return []
    return re.findall(r'href=["\'](%s_\d{12}\.jpg)["\']' % re.escape(cam), text)


def find_anchor(cam):
    """Return latest date with frames, walking back by month."""
    today = date.today()
    for k in range(0, 31):
        y, m = today.year, today.month - k
        while m <= 0:
            m += 12
            y -= 1
        for day_off in (15, 1, 28):
            try:
                d = date(y, m, min(day_off, 28))
            except ValueError:
                continue
            if d >= today:
                continue
            names = day_names(cam, d)
            time.sleep(0.15)
            if names:
                return d
    return None


def fetch_file(url, out):
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return True
    code = curl(url, out).decode().strip()
    if code == "200" and os.path.exists(out):
        with open(out, "rb") as f:
            if f.read(2) == b"\xff\xd8":
                return True
    if os.path.exists(out):
        try:
            os.remove(out)
        except OSError:
            pass
    return False


def build(cam, anchor):
    d = os.path.join(OUT, cam)
    fdir = os.path.join(d, "frames")
    os.makedirs(fdir, exist_ok=True)
    mp4 = os.path.join(d, "archive_7d.mp4")
    gif = os.path.join(d, "archive_1d.gif")
    marker = os.path.join(d, "build_done.json")
    names = []
    for i in range(6, -1, -1):
        names += day_names(cam, anchor - timedelta(days=i))
        time.sleep(0.15)
    names = sorted(set(names))
    if not names:
        return cam, "still-empty", 0
    base = os.path.join(fdir, "raw")
    os.makedirs(base, exist_ok=True)
    for name in names:
        stamp = name[len(cam) + 1:len(cam) + 13]
        url = "https://mesonet.agron.iastate.edu/archive/data/%s/%s/%s/camera/%s/%s" % (
            stamp[0:4], stamp[4:6], stamp[6:8], cam, name)
        fetch_file(url, os.path.join(base, name))
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
    gif_start = max(0, n - 288)
    p2 = subprocess.run(
        ["ffmpeg", "-y", "-start_number", str(gif_start), "-framerate", "6",
         "-i", os.path.join(fdir, "%05d.jpg"),
         "-vf", "fps=6,scale=480:-2:flags=lanczos,split[s0][s1];"
                "[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
         gif], capture_output=True, timeout=600)
    ok1 = p1.returncode == 0 and os.path.exists(mp4)
    ok2 = p2.returncode == 0 and os.path.exists(gif)
    if ok1 and ok2:
        with open(marker, "w") as fh:
            json.dump({"frames": n, "anchor": anchor.isoformat()}, fh)
        for f in files:
            try:
                os.remove(os.path.join(fdir, f))
            except OSError:
                pass
    return cam, ("ok@%s" % anchor if ok1 and ok2 else "mp4=%s gif=%s" % (ok1, ok2)), n


def main():
    state = json.load(open(STATE))
    bad = [c for c, v in state.items() if not str(v[0]).startswith("ok")]
    print("cams needing fallback:", bad, flush=True)
    res = {}
    for cam in bad:
        anchor = find_anchor(cam)
        if not anchor:
            res[cam] = ["no-archive-found", 0]
            print("%-10s no archive found walking back 30 months" % cam, flush=True)
            continue
        cam2, status, n = build(cam, anchor)
        res[cam2] = [status, n]
        print("%-10s %-22s frames=%d" % (cam2, status, n), flush=True)
    state.update(res)
    json.dump(state, open(STATE, "w"), indent=1)
    print("fallback done", flush=True)


if __name__ == "__main__":
    main()
