# -*- coding: utf-8 -*-
"""Session 48k: manifest of all built loop videos (yyc official/wayback + IEM)."""
import json
import os
from datetime import datetime

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
LOOPS = os.path.join(ROOT, "web_viewer", "static", "loops")

manifest = {"generated": datetime.now().isoformat(timespec="seconds"), "loops": []}
missing = []

for src in sorted(os.listdir(LOOPS)):
    sdir = os.path.join(LOOPS, src)
    if not os.path.isdir(sdir):
        continue
    for cam in sorted(os.listdir(sdir), key=lambda x: (len(x), x)):
        cdir = os.path.join(sdir, cam)
        if not os.path.isdir(cdir):
            continue
        entry = {"source": src, "camera": cam, "videos": {}}
        for fname, kind in (("official.mp4", "official_mp4"), ("official.gif", "official_gif"),
                            ("wayback.mp4", "wayback_mp4"), ("wayback.gif", "wayback_gif"),
                            ("archive_7d.mp4", "iem_7d_mp4"), ("archive_1d.gif", "iem_1d_gif")):
            p = os.path.join(cdir, fname)
            if os.path.exists(p):
                entry["videos"][kind] = {"path": "%s/%s/%s" % (src, cam, fname),
                                         "bytes": os.path.getsize(p)}
        # frame counts
        for fdir, key in (("frames_official", "official_frames"),
                          ("frames_wayback", "wayback_frames"),
                          ("frames", "iem_frames")):
            fp = os.path.join(cdir, fdir)
            if os.path.isdir(fp):
                entry[key] = len([f for f in os.listdir(fp) if f.endswith(".jpg")])
        if entry["videos"]:
            manifest["loops"].append(entry)
        else:
            missing.append("%s/%s" % (src, cam))

manifest["totals"] = {
    "cameras_with_loops": len(manifest["loops"]),
    "yyc_official": sum(1 for e in manifest["loops"]
                        if e["source"] == "yyc" and "official_mp4" in e["videos"]),
    "yyc_wayback": sum(1 for e in manifest["loops"]
                       if e["source"] == "yyc" and "wayback_mp4" in e["videos"]),
    "iem": sum(1 for e in manifest["loops"]
               if e["source"] == "iem" and "iem_7d_mp4" in e["videos"]),
    "total_bytes": sum(v["bytes"] for e in manifest["loops"] for v in e["videos"].values()),
}
manifest["without_loops"] = missing

out = os.path.join(ROOT, "docs", "loops_manifest.json")
json.dump(manifest, open(out, "w"), indent=1)
print("cameras_with_loops:", manifest["totals"]["cameras_with_loops"])
print("yyc_official:", manifest["totals"]["yyc_official"],
      "yyc_wayback:", manifest["totals"]["yyc_wayback"],
      "iem:", manifest["totals"]["iem"])
print("total MB: %.1f" % (manifest["totals"]["total_bytes"] / 1e6))
print("without loops:", len(missing), missing[:12])
print("written:", out)
