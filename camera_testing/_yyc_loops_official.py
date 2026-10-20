# -*- coding: utf-8 -*-
"""Session 48d: build official 20-min slideshow loops (MP4+GIF) for all
Calgary cams from https://trafficcam.calgary.ca/ss/<9..0>/locN.jpg + live.

Frames ordered oldest->newest: ss9..ss0, live (11 frames, 2-min spacing).
Output: web_viewer/static/loops/yyc/<loc>/official.{mp4,gif}
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT = os.path.join(ROOT, "web_viewer", "static", "loops", "yyc")
TEMP = os.environ["TEMP"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
LOCS = list(range(0, 224))


def fetch_frame(url, out_path, timeout=25, retries=2):
    for attempt in range(retries):
        p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", str(timeout),
                            "-o", out_path, "-w", "%{http_code}", url],
                           capture_output=True, text=True, timeout=timeout + 8)
        code = (p.stdout or "").strip()
        if code == "200" and os.path.exists(out_path):
            with open(out_path, "rb") as f:
                if f.read(2) == b"\xff\xd8":
                    return True
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
    return False


def build_cam(loc):
    d = os.path.join(OUT, str(loc))
    fdir = os.path.join(d, "frames_official")
    os.makedirs(fdir, exist_ok=True)
    got = 0
    # ss9 .. ss0 then live (sequential indices)
    targets = []
    for i in range(9, -1, -1):
        targets.append("https://trafficcam.calgary.ca/ss/%d/loc%d.jpg" % (i, loc))
    targets.append("https://trafficcam.calgary.ca/loc%d.jpg" % loc)
    for idx, url in enumerate(targets):
        if fetch_frame(url, os.path.join(fdir, "%02d.jpg" % idx)):
            got += 1
    # renumber to be sequential (in case of gaps)
    files = sorted(f for f in os.listdir(fdir) if f.endswith(".jpg"))
    for i, f in enumerate(files):
        target = "%02d.jpg" % i
        if f != target:
            os.replace(os.path.join(fdir, f), os.path.join(fdir, target))
    got = len(files)
    if got < 2:
        return loc, "skip(<2 frames)", got
    mp4 = os.path.join(d, "official.mp4")
    gif = os.path.join(d, "official.gif")
    p1 = subprocess.run(["ffmpeg", "-y", "-framerate", "1", "-i", os.path.join(fdir, "%02d.jpg"),
                         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                         mp4], capture_output=True, timeout=120)
    p2 = subprocess.run(["ffmpeg", "-y", "-framerate", "1", "-i", os.path.join(fdir, "%02d.jpg"),
                         "-vf", "fps=1,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
                         gif], capture_output=True, timeout=180)
    ok_mp4 = p1.returncode == 0 and os.path.exists(mp4)
    ok_gif = p2.returncode == 0 and os.path.exists(gif)
    status = "ok" if (ok_mp4 and ok_gif) else ("mp4=%s gif=%s" % (ok_mp4, ok_gif))
    return loc, status, got


def main():
    os.makedirs(OUT, exist_ok=True)
    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(build_cam, loc): loc for loc in LOCS}
        for f in as_completed(futs):
            loc, status, got = f.result()
            results[loc] = (status, got)
            print("loc%-4d %-16s frames=%d" % (loc, status, got), flush=True)
    ok = sum(1 for s, _ in results.values() if s == "ok")
    print("\nSUMMARY ok=%d/%d" % (ok, len(LOCS)))
    import json
    json.dump({str(k): v for k, v in results.items()},
              open(os.path.join(ROOT, "camera_testing", "yyc_official_loops.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
