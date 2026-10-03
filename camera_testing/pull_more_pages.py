#!/usr/bin/env python3
import urllib.request
import json
import re
import time

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# Get CDX list of all archived nolandda.org HTML pages
print("=" * 60)
print("All CDX entries for nolandda.org (HTML only, 200 status)")
print("=" * 60)

all_urls = set()
try:
    req = urllib.request.Request(
        "https://web.archive.org/cdx/search/cdx?url=nolandda.org/*&filter=mimetype:text/html&filter=statuscode:200&output=json&from=20050101&to=20261231&limit=100000",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
        print(f"  CDX rows: {len(d)}")
        for row in d[1:]:
            url = row[2] if len(row) > 2 else "?"
            all_urls.add(url)
        print(f"  unique URLs: {len(all_urls)}")
except Exception as e:
    print(f"  err: {e}")

# Save list
with open(f"{dossier}\\10_full_recon\\nolandda_url_list.txt", "w") as f:
    for u in sorted(all_urls):
        f.write(u + "\n")
print(f"  saved to nolandda_url_list.txt")

# Pull all unique URLs - especially blog posts and other content
# Use a more targeted approach: try to find interesting ones first
priorities = [
    # Resume
    "https://nolandda.org/resume/dnoland_resume.pdf",
    # Log (blog)
    "https://nolandda.org/log/",
    "https://nolandda.org/log/archive.html",
    # Main pages
    "https://nolandda.org/",
    "https://nolandda.org/index.html",
    "https://nolandda.org/about.html",
    # Pusite
    "https://nolandda.org/pusite/",
    "https://nolandda.org/pusite/index.html",
    "https://nolandda.org/pusite/school.html",
    "https://nolandda.org/pusite/about.html",
    "https://nolandda.org/pusite/etc.html",
    "https://nolandda.org/pusite/weekly.html",
    "https://nolandda.org/pusite/tools.html",
    "https://nolandda.org/pusite/daily.html",
    "https://nolandda.org/pusite/lnf.html",
    "https://nolandda.org/pusite/credit.html",
    "https://nolandda.org/pusite/audio.html",
    "https://nolandda.org/pusite/search.html",
    "https://nolandda.org/pusite/voyeurism.html",
    "https://nolandda.org/pusite/stats.html",
    "https://nolandda.org/pusite/cs490-dsp/",
    "https://nolandda.org/pusite/cs490-dsp/index.html",
    "https://nolandda.org/pusite/emacs.html",
    "https://nolandda.org/pusite/emacs.intro.html",
    # Xoomsite
    "https://nolandda.org/xoomsite/",
    "https://nolandda.org/xoomsite/index.html",
    # History
    "https://nolandda.org/history.html",
    # Other
    "https://nolandda.org/nato_pa.html",
    "https://nolandda.org/sunlight.html",
    "https://nolandda.org/voyeurism.html",
    "https://nolandda.org/ascii.html",
    "https://nolandda.org/colors.html",
    "https://nolandda.org/lnf.html",
    "https://nolandda.org/friends.html",
    "https://nolandda.org/etc.html",
    "https://nolandda.org/tools.html",
    "https://nolandda.org/photos/index.html",
    "https://nolandda.org/projects/index.html",
    "https://nolandda.org/PALX/index.html",
    # Birth post specifically
    "https://nolandda.org/log/qblog_2017.09.11.23.53.28.html",
]

# Fetch missing ones
existing = set()
import os
for f in os.listdir(f"{dossier}\\10_full_recon"):
    if f.startswith("nolandda_"):
        existing.add(f[len("nolandda_"):].replace(".html",""))

for url in priorities:
    fname = url.replace("https://nolandda.org/", "").replace("/", "_").strip("_") or "home"
    if not fname:
        fname = "home"
    if fname.endswith(".html"):
        pass
    elif fname.endswith(".pdf"):
        pass
    else:
        fname = fname + ".html"

    outpath = f"{dossier}\\10_full_recon\\nolandda_{fname}"
    if os.path.exists(outpath):
        # Already pulled
        continue
    try:
        cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&output=json&limit=1&filter=statuscode:200"
        req = urllib.request.Request(cdx_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            cd = json.loads(r.read())
            if not cd or len(cd) < 2:
                print(f"  NO SNAPSHOT: {url}")
                continue
            ts = cd[1][1]
            wayback_url = f"https://web.archive.org/web/{ts}id_/{url}"
            req = urllib.request.Request(wayback_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r2:
                d = r2.read()
                # detect encoding
                try:
                    text = d.decode("utf-8")
                except UnicodeDecodeError:
                    text = d.decode("latin-1", errors="replace")
                with open(outpath, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"  OK {fname} ({len(d)} bytes, ts={ts[:8]})")
    except Exception as e:
        print(f"  ERR {url}: {str(e)[:60]}")
    time.sleep(0.3)