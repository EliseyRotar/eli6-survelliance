#!/usr/bin/env python3
import urllib.request
import json
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# Games On Demand site - Dan's personal hobby project
print("=" * 60)
print("gamesondemand.github.io")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/repos/gamesondemand/gamesondemand.github.io",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Created: {d.get('created_at')}")
        print(f"  Updated: {d.get('updated_at')}")
        print(f"  Description: {d.get('description')}")
        print(f"  Homepage: {d.get('homepage')}")
        print(f"  Topics: {d.get('topics')}")
        print(f"  Owner: {d.get('owner',{}).get('login')}")
        # Get pages
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/gamesondemand/gamesondemand.github.io/pages",
                headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r2:
                page = json.loads(r2.read())
                print(f"  Pages URL: {page.get('html_url')}")
        except Exception as e:
            print(f"  pages err: {e}")
except Exception as e:
    print(f"  err: {e}")

# List all GamesOnDemand members
try:
    req = urllib.request.Request("https://api.github.com/orgs/gamesondemand/members",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  GamesOnDemand members: {len(d)}")
        for u in d:
            print(f"    - {u.get('login')}")
except Exception as e:
    print(f"  members err: {e}")

# Pull website content
try:
    req = urllib.request.Request("https://gamesondemand.github.io",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8", errors="replace")
        open(f"{dossier}\\10_full_recon\\gamesondemand.html","w", encoding="utf-8").write(d)
        print(f"  gamesondemand.github.io size: {len(d)}")
        # Find titles
        for m in re.finditer(r'<title>(.*?)</title>', d):
            print(f"  TITLE: {m.group(1)[:150]}")
        # Find mentions
        for m in re.finditer(r'(?i)(dan|noland|host|present|gencon)', d):
            ctx = d[max(0,m.start()-30):m.end()+60]
            print(f"  MENTION: {ctx.strip()[:120]}")
except Exception as e:
    print(f"  err: {e}")

# Tabletop RPGs repo
print()
print("=" * 60)
print("nolandda/TabletopRPGs")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/repos/nolandda/TabletopRPGs",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Created: {d.get('created_at')}")
        print(f"  Updated: {d.get('updated_at')}")
        print(f"  Description: {d.get('description')}")
        print(f"  Topics: {d.get('topics')}")
        print(f"  Watchers: {d.get('subscribers_count')}")
        print(f"  Stars: {d.get('stargazers_count')}")
        print(f"  Forks: {d.get('forks_count')}")
        # topics
        print(f"  Readme size: {len(d.get('description') or '')}")
        # Get readme
        try:
            req = urllib.request.Request("https://raw.githubusercontent.com/nolandda/TabletopRPGs/master/README.md",
                                          headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r2:
                readme = r2.read().decode("utf-8", errors="replace")
                open(f"{dossier}\\10_full_recon\\tabletoprpg_readme.md","w").write(readme)
                print(f"  Readme: {len(readme)}")
                # Print first 1000 chars
                print(readme[:1500])
        except Exception as e:
            print(f"  readme err: {e}")
except Exception as e:
    print(f"  err: {e}")

# Pull nolandda/misc
print()
print("=" * 60)
print("nolandda/misc (2015)")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/repos/nolandda/misc",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Created: {d.get('created_at')}")
        print(f"  Description: {d.get('description')}")
except Exception as e:
    print(f"  err: {e}")

# Check all of Dan's repos (page 2 if needed)
print()
print("=" * 60)
print("All nolandda repos (full list)")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/users/nolandda/repos?per_page=100&sort=created",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Total: {len(d)}")
        for repo in d:
            print(f"    {repo.get('created_at')[:10]} - {repo.get('name'):30} ({repo.get('language') or '-':10}) {repo.get('description','')[:60]}")
except Exception as e:
    print(f"  err: {e}")

# ALSchwalm - Star Lab colleague who Dan helped
print()
print("=" * 60)
print("ALSchwalm (Dan helped this person)")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/users/ALSchwalm",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Name: {d.get('name')}")
        print(f"  Bio: {d.get('bio')}")
        print(f"  Company: {d.get('company')}")
        print(f"  Location: {d.get('location')}")
        print(f"  Blog: {d.get('blog')}")
        print(f"  Twitter: {d.get('twitter_username')}")
        print(f"  Public repos: {d.get('public_repos')}")
except Exception as e:
    print(f"  err: {e}")

# Polyverse - security company that merged Dan's ARM fix
print()
print("=" * 60)
print("Polyverse (company that merged Dan's ARM fix)")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/orgs/polyverse",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Name: {d.get('name')}")
        print(f"  Description: {d.get('description')}")
        print(f"  Blog: {d.get('blog')}")
        print(f"  Email: {d.get('email')}")
        print(f"  Location: {d.get('location')}")
        print(f"  Created: {d.get('created_at')}")
except Exception as e:
    print(f"  err: {e}")

# rmesg repo content
print()
print("=" * 60)
print("rmesg repo description (Dan contributed)")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/repos/starlab-io/rmesg",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Description: {d.get('description')}")
        print(f"  License: {d.get('license',{}).get('name') if d.get('license') else None}")
        print(f"  Created: {d.get('created_at')}")
        print(f"  Updated: {d.get('updated_at')}")
        # Readme
        try:
            req = urllib.request.Request("https://raw.githubusercontent.com/starlab-io/rmesg/master/README.md",
                                          headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r2:
                readme = r2.read().decode("utf-8")
                open(f"{dossier}\\09_employer\\rmesg_readme.md","w").write(readme)
                print(f"  Readme: {len(readme)} chars")
                print(readme[:500])
        except Exception as e:
            print(f"  readme err: {e}")
except Exception as e:
    print(f"  err: {e}")

# Dan's blog - seekr-page
print()
print("=" * 60)
print("Dan's personal site www.nolandda.org content")
print("=" * 60)
try:
    req = urllib.request.Request("https://nolandda.org",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8", errors="replace")
        # Look for personal info we missed
        print(f"  Size: {len(d)}")
        # Find bio/about
        bio = re.findall(r'(?i)(dan noland|purdue|cs\s|ms\s|software)', d)
        for b in set(bio):
            ctx_idx = d.lower().find(b)
            if ctx_idx >= 0:
                print(f"  CTX[{b}]: ...{d[max(0,ctx_idx-40):ctx_idx+80]}...")
except Exception as e:
    print(f"  err: {e}")