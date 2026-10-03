#!/usr/bin/env python3
import urllib.request
import json
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# Pull Dan's commit in rmesg
print("=" * 60)
print("Dan Noland's rmesg commit in starlab-io")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/repos/starlab-io/rmesg/commits?author=nolandda",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        commits = json.loads(r.read())
        print(f"  Found: {len(commits)} commits")
        for c in commits:
            author = c.get("commit",{}).get("author",{})
            print(f"  - {c.get('sha','')[:8]}: {c.get('commit',{}).get('message','')[:100]}")
            print(f"    by {author.get('name')} <{author.get('email')}> at {author.get('date')}")
            # Save
            open(f"{dossier}\\09_employer\\starlab_rmesg_commit.json","w").write(json.dumps(c, indent=2))
except Exception as e:
    print(f"  err: {e}")

# All commits with nolandda
print()
print("=" * 60)
print("All of Dan's GitHub commits (all repos)")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/search/commits?q=author:nolandda&per_page=50",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.github.cloak-preview+json"
        })
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Total commits by nolandda: {d.get('total_count')}")
        for item in d.get("items", []):
            repo = item.get("repository", {}).get("full_name", "?")
            msg = item.get("commit",{}).get("message","")[:60]
            author = item.get("commit",{}).get("author",{})
            print(f"  - {repo}: {msg}")
            print(f"      {author.get('date')[:10]} - {author.get('email')}")
except Exception as e:
    print(f"  err: {e}")

# Also commits by dnoland
try:
    req = urllib.request.Request(
        "https://api.github.com/search/commits?q=author:dnoland&per_page=50",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.github.cloak-preview+json"
        })
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Total commits by dnoland: {d.get('total_count')}")
        for item in d.get("items", []):
            repo = item.get("repository", {}).get("full_name", "?")
            msg = item.get("commit",{}).get("message","")[:60]
            author = item.get("commit",{}).get("author",{})
            print(f"  - {repo}: {msg}")
            print(f"      {author.get('date')[:10]} - {author.get('email')}")
except Exception as e:
    print(f"  err: {e}")

# Dan's starred repos (work profile)
print()
print("=" * 60)
print("Dan Noland's GitHub starred repos (publicly available)")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/users/nolandda/starred?per_page=100",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Total starred: {len(d)}")
        for repo in d[:30]:
            print(f"  - {repo.get('full_name')} ({repo.get('language')}) - {repo.get('description','')[:60]}")
except Exception as e:
    print(f"  err: {e}")

# Following
try:
    req = urllib.request.Request(
        "https://api.github.com/users/nolandda/following?per_page=100",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Following: {len(d)}")
        for u in d[:30]:
            print(f"  - {u.get('login')} - {u.get('name')}")
except Exception as e:
    print(f"  err: {e}")

# GitHub public events for Dan (if account public)
try:
    req = urllib.request.Request(
        "https://api.github.com/users/nolandda/events/public",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Public events: {len(d) if isinstance(d,list) else 'n/a'}")
except Exception as e:
    print(f"  events err: {e}")