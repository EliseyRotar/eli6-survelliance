#!/usr/bin/env python3
import urllib.request
import json
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# Mythril hypervisor investigation
print("=" * 60)
print("mythril hypervisor investigation")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/repos/mythril-hypervisor/mythril",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Name: {d.get('name')}")
        print(f"  Description: {d.get('description')}")
        print(f"  Created: {d.get('created_at')}")
        print(f"  Updated: {d.get('updated_at')}")
        print(f"  Topics: {d.get('topics')}")
        print(f"  Stars: {d.get('stargazers_count')}")
        print(f"  Forks: {d.get('forks_count')}")
        print(f"  Watchers: {d.get('subscribers_count')}")
except Exception as e:
    print(f"  err: {e}")

# Mythril org
try:
    req = urllib.request.Request("https://api.github.com/orgs/mythril-hypervisor",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"\nMythril org:")
        print(f"  Name: {d.get('name')}")
        print(f"  Description: {d.get('description')}")
        print(f"  Blog: {d.get('blog')}")
        print(f"  Email: {d.get('email')}")
        print(f"  Created: {d.get('created_at')}")
        print(f"  Public repos: {d.get('public_repos')}")
        # Members
        try:
            req = urllib.request.Request("https://api.github.com/orgs/mythril-hypervisor/members",
                                          headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r2:
                members = json.loads(r2.read())
                print(f"  Members: {len(members)}")
                for m in members:
                    print(f"    - {m.get('login')}")
                open(f"{dossier}\\10_full_recon\\mythril_members.json","w").write(json.dumps(members, indent=2))
        except Exception as e:
            print(f"  members err: {e}")
except Exception as e:
    print(f"  err: {e}")

# Mythril repos
try:
    req = urllib.request.Request("https://api.github.com/orgs/mythril-hypervisor/repos?per_page=100",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Mythril repos: {len(d)}")
        for repo in d:
            print(f"    - {repo.get('name'):30} ({repo.get('language') or '-':10}) {repo.get('description','')[:60]}")
except Exception as e:
    print(f"  err: {e}")

# Mythril contributors
print()
print("=" * 60)
print("mythril top contributors")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/repos/mythril-hypervisor/mythril/contributors?per_page=30&anon=true",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Contributors: {len(d)}")
        for c in d:
            login = c.get("login","anon")
            print(f"    {c.get('contributions'):5} - {login} - {c.get('name','') or ''}")
except Exception as e:
    print(f"  err: {e}")

# More of Dan's history - check his first 12 repos for full picture
print()
print("=" * 60)
print("Detail of Dan's repos - readme, contents")
print("=" * 60)
repos = [
    "Sprint", "misc", "pkcs11-proxy", "rpmquery",
    "unicornhat-ps", "mythril", "transient",
    "seccomp-example", "gamesondemand.github.io",
    "roll20-character-sheets"
]
for repo in repos:
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/nolandda/{repo}/contents/README.md",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
            import base64
            content = base64.b64decode(d.get("content","")).decode("utf-8", errors="replace")
            print(f"\n--- {repo} README ---")
            print(content[:600])
    except Exception as e:
        # try alternative names
        for branch in ["master", "main"]:
            try:
                req = urllib.request.Request(
                    f"https://raw.githubusercontent.com/nolandda/{repo}/{branch}/README.md",
                    headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    content = r.read().decode("utf-8", errors="replace")
                    print(f"\n--- {repo} ({branch}) README ---")
                    print(content[:600])
                    break
            except Exception:
                pass

# Dan's pull requests
print()
print("=" * 60)
print("Dan's pull requests")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/search/issues?q=author:nolandda+type:pr&per_page=30",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Total PRs by nolandda: {d.get('total_count')}")
        for item in d.get("items", [])[:20]:
            print(f"  [{item.get('state')}] {item.get('title','')[:80]}")
            print(f"      in {item.get('repository_url','').split('/')[-2:]}")
            print(f"      created {item.get('created_at')[:10]}")
except Exception as e:
    print(f"  err: {e}")

# Check Adam Schwalm's connection to Star Lab (he was a Star Lab member?)
print()
print("=" * 60)
print("Adam Schwalm - was he at Star Lab?")
print("=" * 60)
# Look at his social
try:
    req = urllib.request.Request("https://api.github.com/users/ALSchwalm/followers",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Followers: {len(d)}")
        for f in d[:10]:
            print(f"    - {f.get('login')}")
except Exception as e:
    print(f"  err: {e}")

# Check if Adam is referenced on Mercury Systems or starlab.io
print()
print("=" * 60)
print("Adam Schwalm's starlab commits")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/search/commits?q=author:ALSchwalm+org:starlab-io&per_page=10",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.github.cloak-preview+json"
        })
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Total: {d.get('total_count')}")
        for item in d.get("items", []):
            repo = item.get("repository", {}).get("full_name", "?")
            msg = item.get("commit",{}).get("message","")[:80]
            author = item.get("commit",{}).get("author",{})
            print(f"  - {repo}: {msg}")
            print(f"      {author.get('date')[:10]} - {author.get('email')}")
except Exception as e:
    print(f"  err: {e}")

# Check Adam's LinkedIn-style data
print()
print("=" * 60)
print("Adam Schwalm detailed profile")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/users/ALSchwalm",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        for k, v in d.items():
            if v and k not in ['node_id','avatar_url','url','html_url','followers_url','following_url','gists_url','starred_url','subscriptions_url','organizations_url','repos_url','events_url','received_events_url','type','site_admin','id','gravatar_id']:
                print(f"  {k}: {v}")
except Exception as e:
    print(f"  err: {e}")