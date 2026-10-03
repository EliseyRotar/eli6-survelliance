#!/usr/bin/env python3
import urllib.request
import json
import re
import concurrent.futures
import os

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"
out_dir = f"{dossier}\\10_full_recon"

# Pages we still need - HIGHEST VALUE FIRST
priorities = [
    "https://nolandda.org/",
    "https://nolandda.org/index.html",
    "https://nolandda.org/about.html",
    "https://nolandda.org/etc.html",
    "https://nolandda.org/history.html",
    "https://nolandda.org/sunlight.html",
    "https://nolandda.org/voyeurism.html",
    "https://nolandda.org/nato_pa.html",
    "https://nolandda.org/ascii.html",
    "https://nolandda.org/colors.html",
    "https://nolandda.org/lnf.html",
    "https://nolandda.org/tools.html",
    "https://nolandda.org/friends.html",
    "https://nolandda.org/PALX/",
    "https://nolandda.org/PALX/index.html",
    "https://nolandda.org/PALX/members.html",
    "https://nolandda.org/PALX/adventures.html",
    "https://nolandda.org/pusite/",
    "https://nolandda.org/pusite/index.html",
    "https://nolandda.org/pusite/school.html",
    "https://nolandda.org/pusite/weekly.html",
    "https://nolandda.org/pusite/daily.html",
    "https://nolandda.org/pusite/voyeurism.html",
    "https://nolandda.org/pusite/lnf.html",
    "https://nolandda.org/pusite/audio.html",
    "https://nolandda.org/pusite/search.html",
    "https://nolandda.org/pusite/stats.html",
    "https://nolandda.org/pusite/credit.html",
    "https://nolandda.org/pusite/emacs.html",
    "https://nolandda.org/pusite/emacs.intro.html",
    "https://nolandda.org/pusite/cs490-dsp/",
    "https://nolandda.org/xoomsite/",
    "https://nolandda.org/xoomsite/index.html",
    "https://nolandda.org/photos/index.html",
    "https://nolandda.org/projects/index.html",
    "https://nolandda.org/log/qblog_2017.09.11.23.53.28.html",  # birth post
]

def fetch_one(url):
    """Fetch the latest snapshot for a URL."""
    fname = url.replace("https://nolandda.org/", "").replace("/", "_").strip("_") or "home"
    if not fname.endswith(".html"):
        fname = fname + ".html"
    outpath = f"{out_dir}\\nolandda_{fname}"
    if os.path.exists(outpath) and os.path.getsize(outpath) > 100:
        return f"  SKIP {fname}"
    try:
        cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&output=json&limit=1&filter=statuscode:200"
        req = urllib.request.Request(cdx_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            cd = json.loads(r.read())
            if not cd or len(cd) < 2:
                return f"  NO_SNAP {url}"
            ts = cd[1][1]
            wayback_url = f"https://web.archive.org/web/{ts}id_/{url}"
            req = urllib.request.Request(wayback_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r2:
                d = r2.read()
                try:
                    text = d.decode("utf-8")
                except UnicodeDecodeError:
                    text = d.decode("latin-1", errors="replace")
                with open(outpath, "w", encoding="utf-8") as f:
                    f.write(text)
                return f"  OK {fname} ({len(d)}, {ts[:8]})"
    except Exception as e:
        return f"  ERR {url}: {str(e)[:60]}"

print(f"Fetching {len(priorities)} pages with 5 workers...")
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    futures = {ex.submit(fetch_one, u): u for u in priorities}
    for fut in concurrent.futures.as_completed(futures):
        result = fut.result()
        print(result)

print("\nDone")