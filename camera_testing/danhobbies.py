#!/usr/bin/env python3
import urllib.request
import json
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# All of Dan's repos - full
print("=" * 60)
print("All 12 nolandda repos")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/users/nolandda/repos?per_page=100&sort=created&direction=asc",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Total: {len(d)}")
        for repo in d:
            ca = repo.get("created_at","")[:10]
            ua = repo.get("updated_at","")[:10]
            lang = repo.get("language") or "-"
            desc = (repo.get("description") or "")[:60]
            stars = repo.get("stargazers_count", 0)
            forks = repo.get("forks_count", 0)
            print(f"  {ca} (upd {ua}) - {repo.get('name'):30} {lang:10} ({stars} stars, {forks} forks)")
            print(f"        {desc}")
            print(f"        {repo.get('html_url')}")
except Exception as e:
    print(f"  err: {e}")

# Get details of each one
print()
print("=" * 60)
print("Recent activity - gamesondemand 2026")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/repos/gamesondemand/gamesondemand.github.io/commits?per_page=20",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Total: {len(d)}")
        for c in d:
            author = c.get("commit",{}).get("author",{})
            print(f"  {c.get('commit',{}).get('author',{}).get('date','')[:10]} - {c.get('sha','')[:8]}: {c.get('commit',{}).get('message','')[:80]}")
            print(f"      by {author.get('name')} <{author.get('email')}>")
except Exception as e:
    print(f"  err: {e}")

# Games on Demand content - search for "Dan" or specific info
print()
print("=" * 60)
print("Games on Demand org website")
print("=" * 60)
try:
    req = urllib.request.Request("https://gamesondemand.github.io/for-hosts/",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8", errors="replace")
        open(f"{dossier}\\10_full_recon\\gamesondemand_hosts.html","w", encoding="utf-8").write(d)
        print(f"  for-hosts size: {len(d)}")
        for m in re.finditer(r'<title>(.*?)</title>', d):
            print(f"  TITLE: {m.group(1)[:200]}")
        # Find names
        for m in re.finditer(r'(?i)(dan|noland|organizer|host|coordinator)', d):
            ctx_idx = m.start()
            ctx = re.sub(r'<[^>]+>', '', d[max(0,ctx_idx-50):ctx_idx+150])
            if ctx.strip():
                print(f"  CTX: {ctx.strip()[:200]}")
except Exception as e:
    print(f"  err: {e}")

# Games on Demand pages
try:
    req = urllib.request.Request("https://gamesondemand.github.io/for-gms/",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8", errors="replace")
        open(f"{dossier}\\10_full_recon\\gamesondemand_gms.html","w", encoding="utf-8").write(d)
        print(f"  for-gms size: {len(d)}")
except Exception as e:
    print(f"  err: {e}")

# Pull more gamesondemand pages
for path in ["", "schedule/", "locations/", "history/", "about/", "contact/"]:
    try:
        req = urllib.request.Request(f"https://gamesondemand.github.io/{path}",
                                      headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = r.read().decode("utf-8", errors="replace")
            safe = path.replace("/", "_") or "home"
            open(f"{dossier}\\10_full_recon\\gamesondemand_{safe}.html","w", encoding="utf-8").write(d)
            print(f"  gamesondemand/{path} -> {len(d)} bytes")
    except Exception as e:
        print(f"  gamesondemand/{path} -> err {e}")

# Check Adam Schwalm's repos at Amazon/Star Lab context
print()
print("=" * 60)
print("Adam Schwalm's rust/embedded repos")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/users/ALSchwalm/repos?per_page=100&sort=updated",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Total: {len(d)}")
        for repo in d[:25]:
            desc = (repo.get("description") or "")[:60]
            lang = repo.get("language") or "-"
            print(f"  {repo.get('updated_at','')[:10]} - {repo.get('name'):30} ({lang:8}) {desc}")
except Exception as e:
    print(f"  err: {e}")

# See if Adam Schwalm worked at Star Lab
# His bio says "I'm a software engineer and platform developer, mostly working with rust and C"
# He's at Amazon Huntsville - probably AWS Ground Station (Amazon's satellite/space business in Huntsville area)
# Huntsville = aerospace hub = consistent with Mercury Systems

# Dan's email davidnoland@yahoo.com - verify
print()
print("=" * 60)
print("Verify David Noland email")
print("=" * 60)
# Github commit on Kong docs
try:
    req = urllib.request.Request(
        "https://api.github.com/search/commits?q=author:davidnoland@yahoo.com&per_page=20",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.github.cloak-preview+json"
        })
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Commits by davidnoland@yahoo.com: {d.get('total_count')}")
        for item in d.get("items", []):
            repo = item.get("repository", {}).get("full_name", "?")
            msg = item.get("commit",{}).get("message","")[:60]
            author = item.get("commit",{}).get("author",{})
            print(f"  - {repo}: {msg}")
            print(f"      {author.get('date')[:10]} - {author.get('name')}")
except Exception as e:
    print(f"  err: {e}")

# Check GitHub user 'noland' too
try:
    req = urllib.request.Request("https://api.github.com/users/noland",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"\nnoland user:")
        print(f"  Name: {d.get('name')}")
        print(f"  Bio: {d.get('bio')}")
        print(f"  Company: {d.get('company')}")
        print(f"  Location: {d.get('location')}")
        print(f"  Blog: {d.get('blog')}")
        print(f"  Created: {d.get('created_at')}")
        print(f"  Public repos: {d.get('public_repos')}")
except Exception as e:
    print(f"  err: {e}")

# Dan's corkboard
print()
print("=" * 60)
print("Dan's comments and activity on GitHub")
print("=" * 60)
# Look at issues Dan commented on
try:
    req = urllib.request.Request(
        "https://api.github.com/search/issues?q=commenter:nolandda&per_page=20",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Issues commented on by nolandda: {d.get('total_count')}")
        for item in d.get("items", [])[:10]:
            print(f"  - [{item.get('state')}] {item.get('title','')[:80]}")
            print(f"        in {item.get('repository_url','').split('/')[-2:]}")
            print(f"        {item.get('html_url')}")
except Exception as e:
    print(f"  err: {e}")