#!/usr/bin/env python3
import urllib.request
import json
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# DockerHub user page
req = urllib.request.Request("https://hub.docker.com/u/nolandda", headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read().decode("utf-8", errors="replace")
        open(f"{dossier}\\10_full_recon\\dockerhub_user.html", "w", encoding="utf-8").write(data)
        print(f"DockerHub size: {len(data)}")
        # Look for repositories
        repos = re.findall(r'href="(/r/nolandda/([^"]+))"', data)
        print(f"Repos: {len(repos)}")
        for url, name in repos[:30]:
            print(f"  - {name}: https://hub.docker.com{url}")
except Exception as e:
    print(f"DockerHub err: {e}")

print()
print("=" * 60)
print("Bitbucket public info")
print("=" * 60)
# Bitbucket removed public user pages, but API still works for cloud
try:
    req = urllib.request.Request("https://api.bitbucket.org/2.0/users/nolandda",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8")
        print(f"Bitbucket response: {d[:500]}")
        open(f"{dossier}\\10_full_recon\\bitbucket_api.json", "w").write(d)
except Exception as e:
    print(f"  err: {e}")

print()
print("=" * 60)
print("WordPress deeper scrape")
print("=" * 60)
# WordPress might require JS - check feed
try:
    req = urllib.request.Request("https://nolandda.wordpress.com/feed/",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8")
        open(f"{dossier}\\10_full_recon\\wordpress_feed.xml", "w", encoding="utf-8").write(d)
        print(f"WP feed size: {len(d)}")
        titles = re.findall(r'<title>(.*?)</title>', d, re.DOTALL)
        for t in titles[:20]:
            t = t.strip()
            if t and t != "WordPress.com" and t != "nolandda":
                print(f"  POST: {t[:150]}")
except Exception as e:
    print(f"  err: {e}")

print()
print("=" * 60)
print("GitHub noreply email lookup")
print("=" * 60)
# GitHub sometimes leaks noreply emails for users via commit data
# Check user page
try:
    req = urllib.request.Request("https://api.github.com/users/nolandda/events/public",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8")
        open(f"{dossier}\\10_full_recon\\github_events.json", "w").write(d)
        print(f"Events size: {len(d)}")
        emails = re.findall(r'"email":"([^"]+)"', d)
        print(f"Emails: {set(emails)}")
        names = re.findall(r'"name":"([^"]+)"', d)
        print(f"Names: {set(names)}")
except Exception as e:
    print(f"  err: {e}")

print()
print("=" * 60)
print("Wayback Machine check for nolandda subdomains")
print("=" * 60)
# Check for archived GitLab/Bitbucket on Wayback
for url in [
    "https://gitlab.com/nolandda",
    "https://bitbucket.org/nolandda",
    "https://hub.docker.com/u/nolandda",
    "https://github.com/dnoland",
]:
    try:
        req = urllib.request.Request(
            f"https://web.archive.org/web/2024*/"+url,
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = r.read().decode("utf-8")
            print(f"  {url} -> Wayback size {len(d)}")
    except Exception as e:
        print(f"  {url} -> err {e}")

print()
print("=" * 60)
print("Mercury Systems email pattern")
print("=" * 60)
# Mercury Systems has email pattern dan.noland@mrcy.com
# We already know his SSH config has dan.noland - so the username IS dan.noland
# Let's check mrcy.com directly for any leaked info
for url in [
    "https://www.mrcy.com/team",
    "https://www.mrcy.com/leadership",
    "https://www.mrcy.com/about",
]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = r.read().decode("utf-8")
            # Check if Dan Noland is mentioned
            if "noland" in d.lower():
                print(f"  {url} -> mentions Noland!")
                # Save
                safe = url.replace("https://","").replace("/","_")
                open(f"{dossier}\\09_employer\\{safe}.html","w",encoding="utf-8").write(d)
            else:
                print(f"  {url} -> no Noland mention (size {len(d)})")
    except Exception as e:
        print(f"  {url} -> err {e}")

print()
print("=" * 60)
print("GitHub dnoland repos")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/users/dnoland/repos?per_page=100",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"dnoland repos: {len(d)}")
        for repo in d:
            print(f"  - {repo.get('full_name')} ({repo.get('language')}) - {repo.get('description','')[:80]}")
            print(f"      created: {repo.get('created_at')[:10]}, pushed: {repo.get('pushed_at')[:10]}")
except Exception as e:
    print(f"  err: {e}")

print()
print("=" * 60)
print("GitHub search dnoland contributions")
print("=" * 60)
try:
    req = urllib.request.Request(
        "https://api.github.com/search/commits?q=author-email:dan.noland%40mrcy.com&per_page=20",
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github.cloak-preview+json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"Commits with @mrcy.com email: {d.get('total_count')}")
        for item in d.get("items", [])[:10]:
            repo = item.get("repository", {}).get("full_name", "?")
            msg = item.get("commit",{}).get("message","")[:80]
            author = item.get("commit",{}).get("author",{})
            print(f"  - {repo}: {msg} ({author.get('email')}, {author.get('date')[:10]})")
except Exception as e:
    print(f"  err: {e}")

# Also try direct email
try:
    req = urllib.request.Request(
        "https://api.github.com/search/users?q=noland+in:email",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"GitHub users with 'noland' email: {d.get('total_count')}")
        for item in d.get("items", [])[:5]:
            print(f"  - {item.get('login')} ({item.get('email')})")
except Exception as e:
    print(f"  err {e}")