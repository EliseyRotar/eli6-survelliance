# -*- coding: utf-8 -*-
"""Session 48p: rolling ring refresh for official Calgary loops.

Every cycle (default: driven by Task Scheduler every 5 min):
  per cam: fetch live /locN.jpg + newest archive /ss/0/locN.jpg;
  if md5 differs from the newest stored frame -> drop oldest, append,
  re-encode official.mp4 + official.gif ATOMICALLY (tmp + os.replace).
Full mode (--full): wipe + re-download all 11 frames (daily/catch-up).

Loop geometry: 11 stored frames sampled ~5 min apart -> ~55-min window,
newest frame <= ~7 min old. Bandwidth: 2 x ~85KB x 222 cams ~ 37MB/cycle.

Logs to camera_testing/yyc_ring.log. Regenerates the gallery index after
each cycle (cheap, keeps sizes/links current).
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT = os.path.join(ROOT, "web_viewer", "static", "loops", "yyc")
LOG = os.path.join(ROOT, "camera_testing", "yyc_ring.log")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
LOCS = list(range(0, 224))
WORKERS = 4


def log(msg):
    line = "%s %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def fetch(url, out, timeout=25, retries=2):
    for _ in range(retries):
        p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", str(timeout),
                            "-o", out, "-w", "%{http_code}", url],
                           capture_output=True, text=True, timeout=timeout + 8)
        if (p.stdout or "").strip() == "200" and os.path.exists(out):
            with open(out, "rb") as f:
                head = f.read(2)
            if head == b"\xff\xd8":
                with open(out, "rb") as f:
                    return hashlib.md5(f.read()).hexdigest()
        time.sleep(1.5)
    if os.path.exists(out):
        try:
            os.remove(out)
        except OSError:
            pass
    return None


def renumber(fdir):
    files = sorted(f for f in os.listdir(fdir)
                   if f.endswith(".jpg") and not f.startswith("tmp_"))
    for i, f in enumerate(files):
        t = "%02d.jpg" % i
        if f != t:
            os.replace(os.path.join(fdir, f), os.path.join(fdir, t))
    return sorted(f for f in os.listdir(fdir)
                  if f.endswith(".jpg") and not f.startswith("tmp_"))


def encode(d, fdir, files):
    """Atomic encode of official.mp4 + official.gif. Returns True on success."""
    if len(files) < 2:
        return False
    mp4 = os.path.join(d, "official.mp4")
    gif = os.path.join(d, "official.gif")
    mp4t = os.path.join(d, "official.tmp.mp4")
    gitt = os.path.join(d, "official.tmp.gif")
    for t in (mp4t, gitt):
        if os.path.exists(t):
            try:
                os.remove(t)
            except OSError:
                pass
    p1 = subprocess.run(["ffmpeg", "-y", "-framerate", "1", "-i", os.path.join(fdir, "%02d.jpg"),
                         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                         mp4t], capture_output=True, timeout=120)
    p2 = subprocess.run(["ffmpeg", "-y", "-framerate", "1", "-i", os.path.join(fdir, "%02d.jpg"),
                         "-vf", "fps=1,split[s0][s1];[s0]palettegen=max_colors=128[p];"
                                "[s1][p]paletteuse=dither=bayer",
                         gitt], capture_output=True, timeout=180)
    ok = True
    if p1.returncode == 0 and os.path.exists(mp4t):
        os.replace(mp4t, mp4)
    else:
        ok = False
        if os.path.exists(mp4t):
            os.remove(mp4t)
    if p2.returncode == 0 and os.path.exists(gitt):
        os.replace(gitt, gif)
    else:
        ok = False
        if os.path.exists(gitt):
            os.remove(gitt)
    return ok


def full_cam(loc):
    d = os.path.join(OUT, str(loc))
    fdir = os.path.join(d, "frames_official")
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        if f.endswith(".jpg"):
            try:
                os.remove(os.path.join(fdir, f))
            except OSError:
                pass
    urls = ["https://trafficcam.calgary.ca/ss/%d/loc%d.jpg" % (i, loc) for i in range(9, -1, -1)]
    urls.append("https://trafficcam.calgary.ca/loc%d.jpg" % loc)
    got = 0
    for i, url in enumerate(urls):
        if fetch(url, os.path.join(fdir, "%02d.jpg" % i)):
            got += 1
    files = renumber(fdir)
    if got < 2:
        return loc, "full-skip", got
    return loc, ("full-ok" if encode(d, fdir, files) else "full-encode-fail"), got


def ring_cam(loc):
    d = os.path.join(OUT, str(loc))
    fdir = os.path.join(d, "frames_official")
    os.makedirs(fdir, exist_ok=True)
    files = renumber(fdir)
    if len(files) < 2:
        return loc, "ring-init", 0
    newest = os.path.join(fdir, files[-1])
    with open(newest, "rb") as f:
        newest_md5 = hashlib.md5(f.read()).hexdigest()
    tmp_live = os.path.join(fdir, "tmp_live.jpg")
    tmp_ss0 = os.path.join(fdir, "tmp_ss0.jpg")
    md5_live = fetch("https://trafficcam.calgary.ca/loc%d.jpg" % loc, tmp_live)
    md5_ss0 = fetch("https://trafficcam.calgary.ca/ss/0/loc%d.jpg" % loc, tmp_ss0)
    appended = 0
    for md5, tmp in ((md5_ss0, tmp_ss0), (md5_live, tmp_live)):
        if md5 and md5 != newest_md5 and os.path.exists(tmp):
            files = renumber(fdir)
            if len(files) >= 11:
                try:
                    os.remove(os.path.join(fdir, files[0]))
                except OSError:
                    pass
                files = renumber(fdir)
            os.replace(tmp, os.path.join(fdir, "%02d.jpg" % len(files)))
            files = renumber(fdir)
            newest_md5 = md5
            appended += 1
        elif os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    if appended:
        ok = encode(d, fdir, files)
        return loc, ("ring-ok+%d" % appended) if ok else "ring-encode-fail", len(files)
    return loc, "ring-nochange", len(files)


def acquire_lock():
    lock = os.path.join(ROOT, "camera_testing", "yyc_ring.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return lock
    except FileExistsError:
        try:
            age = time.time() - os.path.getmtime(lock)
        except OSError:
            return None
        if age > 900:
            try:
                os.remove(lock)
            except OSError:
                pass
            return acquire_lock()
        return None


def main():
    lock = acquire_lock()
    if not lock:
        log("cycle skipped: another cycle holds the lock")
        return
    try:
        run()
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


def run():
    full = "--full" in sys.argv
    t0 = time.time()
    mode = "FULL" if full else "RING"
    log("cycle %s start pid=%d" % (mode, os.getpid()))
    stats = {}
    fn = full_cam if full else ring_cam
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fn, loc): loc for loc in LOCS}
        for f in as_completed(futs):
            loc, status, n = f.result()
            key = status.split("+")[0]
            stats[key] = stats.get(key, 0) + 1
            if not status.startswith(("ring-nochange", "ring-ok")):
                log("  loc%-4d %s frames=%d" % (loc, status, n))
    # regenerate gallery so sizes/links stay current
    try:
        subprocess.run([sys.executable, os.path.join(ROOT, "camera_testing", "_loops_manifest.py")],
                       capture_output=True, timeout=180)
        subprocess.run([sys.executable, os.path.join(ROOT, "camera_testing", "_loops_gallery.py")],
                       capture_output=True, timeout=120)
    except Exception as e:
        log("  gallery regen failed: %s" % e)
    log("cycle %s done in %.0fs stats=%s" % (mode, time.time() - t0, stats))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        log("FATAL: " + traceback.format_exc().replace("\n", " | "))
