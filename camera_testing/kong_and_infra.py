#!/usr/bin/env python3
import urllib.request
import json
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# Kong connection - Dan worked at Mashape (now Kong) in 2017?
print("=" * 60)
print("Kong API gateway investigation")
print("=" * 60)
# Dan's commit on getkong.org 2017-04-23
# Was Dan at Mashape/Kong? Let's check if getkong.org had him
req = urllib.request.Request("https://github.com/dnoland/getkong.org",
                              headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    d = r.read().decode("utf-8")
    # Search for bio/about info
    print(f"getkong.org page size: {len(d)}")
    # Get commit history
    try:
        req = urllib.request.Request("https://api.github.com/repos/dnoland/getkong.org/commits",
                                      headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r2:
            commits = json.loads(r2.read())
            print(f"getkong.org commits: {len(commits)}")
            for c in commits[:5]:
                author = c.get("commit",{}).get("author",{})
                print(f"  - {c.get('sha','')[:8]}: {c.get('commit',{}).get('message','')[:80]} by {author.get('name')} <{author.get('email')}>")
    except Exception as e:
        print(f"  commits err: {e}")

print()
print("=" * 60)
print("dnoland/facebooker investigation (Ruby 2008)")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/repos/dnoland/facebooker/commits",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        commits = json.loads(r.read())
        print(f"facebooker commits: {len(commits)}")
        for c in commits[:5]:
            author = c.get("commit",{}).get("author",{})
            print(f"  - {c.get('sha','')[:8]}: {c.get('commit',{}).get('message','')[:80]}")
            print(f"    by {author.get('name')} <{author.get('email')}> at {author.get('date')}")
except Exception as e:
    print(f"  err: {e}")

print()
print("=" * 60)
print("Check Mashape/Kong employee records")
print("=" * 60)
# Check if Dan's full name appears on Kong team page
for url in [
    "https://konghq.com/team",
    "https://konghq.com/about",
    "https://docs.konghq.com/about",
]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = r.read().decode("utf-8", errors="replace")
            if "noland" in d.lower():
                print(f"  {url} -> mentions Noland!")
                safe = url.replace("https://","").replace("/","_")
                open(f"{dossier}\\10_full_recon\\{safe}.html","w",encoding="utf-8").write(d)
            else:
                print(f"  {url} -> no Noland (size {len(d)})")
    except Exception as e:
        print(f"  {url} -> err {e}")

print()
print("=" * 60)
print("Mercury Systems infrastructure")
print("=" * 60)
# Mercury Systems is Andover, MA. Their website mrcy.com
# Check for any developer portal or git
for url in [
    "https://github.com/mercury-systems",
    "https://github.com/starlab-io",
    "https://github.com/star-lab",
    "https://gitlab.com/mercury-systems",
]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = r.read().decode("utf-8", errors="replace")
            print(f"  {url} -> size {len(d)}")
            # find repos
            repos = re.findall(r'"full_name":"([^"]+)"', d)
            for r2 in repos[:10]:
                print(f"    repo: {r2}")
    except Exception as e:
        print(f"  {url} -> err {e}")

# Check gitlab group API for mercury
try:
    req = urllib.request.Request("https://gitlab.com/api/v4/groups?search=Mercury",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"GitLab Mercury groups: {len(d)}")
        for g in d[:5]:
            print(f"  - {g.get('full_path')}: {g.get('description','')[:80]}")
except Exception as e:
    print(f"  err: {e}")

print()
print("=" * 60)
print("git.starlab.io and git.star.lab history")
print("=" * 60)
# Wayback check for git.starlab.io
for url in [
    "https://git.starlab.io",
    "https://git.star.lab",
    "https://starlab.io",
    "https://www.starlab.io",
]:
    try:
        req = urllib.request.Request(
            f"https://web.archive.org/web/2020/{url}",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = r.read().decode("utf-8", errors="replace")
            print(f"  {url} (Wayback 2020) -> size {len(d)}")
            # find snapshots
            ts = re.findall(r'/web/(\d{14})/', d)
            if ts:
                print(f"    timestamps: {ts[:5]}")
    except Exception as e:
        print(f"  {url} -> err {e}")

print()
print("=" * 60)
print("Internet Archive: kolandda.org -> nolandda.org history")
print("=" * 60)
# Wayback CDX API for the full history
try:
    req = urllib.request.Request(
        "https://web.archive.org/cdx/search/cdx?url=nolandda.org/*&output=json&limit=5000",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
        print(f"CDX rows: {len(d)}")
        if d:
            header = d[0]
            print(f"  header: {header}")
            # Group by url
            urls = {}
            for row in d[1:]:
                url = row[2] if len(row) > 2 else "?"
                ts = row[1]
                if url not in urls or ts > urls[url]:
                    urls[url] = ts
            print(f"  unique URLs: {len(urls)}")
            # Show recent ones
            sorted_urls = sorted(urls.items(), key=lambda x: x[1], reverse=True)
            for url, ts in sorted_urls[:50]:
                print(f"    {ts[:8]} {url}")
except Exception as e:
    print(f"  err: {e}")