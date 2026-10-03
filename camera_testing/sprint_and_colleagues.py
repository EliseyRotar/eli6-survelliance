#!/usr/bin/env python3
import urllib.request
import json
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# mrozekma (Michael Rozek?) - probably Star Lab colleague
print("=" * 60)
print("mrozekma (Star Lab colleague?)")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/users/mrozekma",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        for k, v in d.items():
            if v and k not in ['node_id','avatar_url','url','html_url','followers_url','following_url','gists_url','starred_url','subscriptions_url','organizations_url','repos_url','events_url','received_events_url','type','site_admin','id','gravatar_id']:
                print(f"  {k}: {v}")
except Exception as e:
    print(f"  err: {e}")

# His repos
try:
    req = urllib.request.Request("https://api.github.com/users/mrozekma/repos?per_page=100",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"\n  Repos: {len(d)}")
        for repo in d[:30]:
            desc = (repo.get("description") or "")[:60]
            lang = repo.get("language") or "-"
            print(f"  {repo.get('updated_at','')[:10]} - {repo.get('name'):30} ({lang:10}) {desc}")
except Exception as e:
    print(f"  err: {e}")

# Sprint repo - Dan's first contribution
print()
print("=" * 60)
print("Sprint repo (Dan's first OSS contribution)")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/repos/mrozekma/Sprint",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Description: {d.get('description')}")
        print(f"  Created: {d.get('created_at')}")
        print(f"  Updated: {d.get('updated_at')}")
        print(f"  Stars: {d.get('stargazers_count')}")
        # Commits
        try:
            req = urllib.request.Request("https://api.github.com/repos/mrozekma/Sprint/commits?per_page=30",
                                          headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r2:
                commits = json.loads(r2.read())
                print(f"  Commits: {len(commits)}")
                for c in commits[:30]:
                    author = c.get("commit",{}).get("author",{})
                    msg = c.get("commit",{}).get("message","")[:60]
                    print(f"  {c.get('sha','')[:8]} {author.get('date','')[:10]} - {msg} ({author.get('email')})")
        except Exception as e:
            print(f"  err: {e}")
except Exception as e:
    print(f"  err: {e}")

# Check for Daniel Noland on LinkedIn / other places
print()
print("=" * 60)
print("Search for Daniel/David Noland public mentions")
print("=" * 60)
# Purdue CS alumni records - LinkedIn search via bing
try:
    req = urllib.request.Request(
        "https://duckduckgo.com/html/?q=David+Noland+Purdue+Mercury+Systems",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8")
        print(f"  DuckDuckGo size: {len(d)}")
        urls = re.findall(r'href="(https?://[^"]+noland[^"]*)"', d, re.IGNORECASE)
        urls2 = re.findall(r'href="(https?://[^"]+mercury[^"]*)"', d, re.IGNORECASE)
        print(f"  noland URLs: {urls[:10]}")
        print(f"  mercury URLs: {urls2[:10]}")
except Exception as e:
    print(f"  err: {e}")

# Mercury Systems has a team page
print()
print("=" * 60)
print("Mercury Systems investor/team pages")
print("=" * 60)
for url in [
    "https://investors.mrcy.com/leadership",
    "https://www.mrcy.com/who-we-are",
    "https://www.mrcy.com/about-us",
    "https://www.mrcy.com/contact",
    "https://www.mrcy.com/careers",
    "https://www.mrcy.com/security",
]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = r.read().decode("utf-8", errors="replace")
            # Check for noland
            if "noland" in d.lower():
                print(f"  {url} -> mentions Noland!")
            else:
                print(f"  {url} -> no Noland ({len(d)})")
    except Exception as e:
        print(f"  {url} -> err {e}")

# Look at the latest dan's website for any new info
print()
print("=" * 60)
print("nolandda.org deep scrape")
print("=" * 60)
# Get the full site
try:
    req = urllib.request.Request("http://nolandda.org",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8", errors="replace")
        print(f"  http://nolandda.org size: {len(d)}")
        # look for redirects
        print(f"  final url: {r.geturl()}")
        if r.geturl() != "http://nolandda.org":
            print(f"  REDIRECTED to: {r.geturl()}")
except Exception as e:
    print(f"  err: {e}")

# Check dan's recent commits on gamesondemand.github.io (already pulled)
# But see what his PR was about
print()
print("=" * 60)
print("Dan Noland's recent GenCon 2026 PR content")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/repos/gamesondemand/gamesondemand.github.io/pulls/20",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Title: {d.get('title')}")
        print(f"  Body: {d.get('body')}")
        print(f"  Created: {d.get('created_at')}")
        print(f"  State: {d.get('state')}")
        print(f"  Additions: {d.get('additions')}")
        print(f"  Deletions: {d.get('deletions')}")
        print(f"  Changed files: {d.get('changed_files')}")
        # Files
        try:
            req = urllib.request.Request("https://api.github.com/repos/gamesondemand/gamesondemand.github.io/pulls/20/files",
                                          headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r2:
                files = json.loads(r2.read())
                for f in files:
                    print(f"  FILE: {f.get('filename')} (+{f.get('additions')}/-{f.get('deletions')})")
        except Exception as e:
            print(f"  files err: {e}")
except Exception as e:
    print(f"  err: {e}")

# Check the OpenGenCon / Games on Demand for current events
print()
print("=" * 60)
print("GenCon 2026 dates and Games on Demand")
print("=" * 60)
# GenCon 2026 was July 30 - Aug 2, 2026 (per public info)
# So Dan just prepped/updated the site before GenCon
# Check gamesondemand FAQ
try:
    req = urllib.request.Request("https://gamesondemand.github.io/about/",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8", errors="replace")
        # Find names/organizers
        for m in re.finditer(r'(?i)(segedy|noland|organiz|coordinator|contact|email)', d):
            ctx = re.sub(r'<[^>]+>', '', d[max(0,m.start()-40):m.end()+150])
            print(f"  CTX: {ctx.strip()[:200]}")
except Exception as e:
    print(f"  err: {e}")

# Check Steve Segedy
print()
print("=" * 60)
print("Steve Segedy (Games on Demand lead)")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/users/segedy",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        for k, v in d.items():
            if v and k not in ['node_id','avatar_url','url','html_url','followers_url','following_url','gists_url','starred_url','subscriptions_url','organizations_url','repos_url','events_url','received_events_url','type','site_admin','id','gravatar_id']:
                print(f"  {k}: {v}")
except Exception as e:
    print(f"  err: {e}")