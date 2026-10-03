#!/usr/bin/env python3
import urllib.request
import json
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# Pull all starlab-io repos with detailed info
print("=" * 60)
print("All Star Lab GitHub repos (detailed)")
print("=" * 60)

all_repos = []
for page in range(1, 10):
    try:
        req = urllib.request.Request(
            f"https://api.github.com/orgs/starlab-io/repos?per_page=100&page={page}&sort=updated",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
            if not d:
                break
            all_repos.extend(d)
            print(f"  Page {page}: {len(d)} repos")
    except Exception as e:
        print(f"  err page {page}: {e}")
        break

print(f"Total: {len(all_repos)}")
# Group by language
from collections import Counter
langs = Counter(r.get("language") for r in all_repos)
print(f"Languages: {dict(langs)}")
# Show all repos
for r in all_repos:
    desc = (r.get("description") or "")[:60]
    print(f"  {r.get('name'):35} ({r.get('language') or '-':10}) {desc}")

# Save full repo list
open(f"{dossier}\\09_employer\\starlab_repos_full.json","w").write(json.dumps(all_repos, indent=2))

# Check commits in starlab-io org for author:dnoland (no - GitHub search won't search org-wide for commits)
# But we can look at popular repos and check Dan's contributions

# Check if Dan is in the members list (we got 0 earlier - means members list is hidden)
# Try via events:
print()
print("=" * 60)
print("Check if Dan starred any starlab repos")
print("=" * 60)
# We can check by Dan's user account, but no auth
# Alternative: search for "D. Noland" or "Dan Noland" in starlab repos commits
for repo in all_repos[:5]:  # check top 5
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/starlab-io/{repo['name']}/contributors",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            cs = json.loads(r.read())
            for c in cs:
                if "noland" in c.get("login","").lower():
                    print(f"  HIT! {repo['name']}: {c.get('login')} ({c.get('contributions')} commits)")
    except Exception as e:
        pass

# Get top 10 by stars
print()
print("=" * 60)
print("Top 10 Star Lab repos by stars")
print("=" * 60)
top_repos = sorted(all_repos, key=lambda r: r.get("stargazers_count",0), reverse=True)
for r in top_repos[:10]:
    print(f"  {r.get('stargazers_count'):4} stars  {r.get('name'):35} ({r.get('language') or '-':10}) {r.get('html_url')}")
    print(f"        {r.get('description','')}")

# OpenMercury GitLab - pull repos
print()
print("=" * 60)
print("OpenMercury GitLab repos")
print("=" * 60)
try:
    req = urllib.request.Request("https://gitlab.com/openmercury",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8")
        repos = re.findall(r'href="/openmercury/([^"]+)"[^>]*>\s*<[^>]*>([^<]+)', d)
        for path, name in repos[:30]:
            if path and not path.startswith("?"):
                print(f"  {path} ({name[:40]})")
except Exception as e:
    print(f"  err: {e}")

# OpenMercury API
try:
    req = urllib.request.Request("https://gitlab.com/api/v4/groups/openmercury",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  openmercury: {d.get('full_path')} - {d.get('description','')}")
        print(f"  created: {d.get('created_at')}")
        print(f"  projects: {d.get('projects', '?')}")
except Exception as e:
    print(f"  err: {e}")

# Look at meta-rust commits for "noland" or "dan"
print()
print("=" * 60)
print("meta-rust contributors (Dan might be here)")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/repos/starlab-io/meta-rust/contributors?per_page=100&anon=true",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Contributors: {len(d)}")
        for c in d:
            login = c.get("login","anon")
            print(f"    {c.get('contributions'):5} commits - {login} - {c.get('name','') or ''}")
except Exception as e:
    print(f"  err: {e}")

# Check meta-measured
try:
    req = urllib.request.Request(
        "https://api.github.com/repos/starlab-io/meta-measured/contributors?per_page=100&anon=true",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  meta-measured Contributors: {len(d)}")
        for c in d:
            login = c.get("login","anon")
            print(f"    {c.get('contributions'):5} commits - {login} - {c.get('name','') or ''}")
except Exception as e:
    print(f"  err: {e}")