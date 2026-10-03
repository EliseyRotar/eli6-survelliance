import re
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\_blog_a_coruna.html', encoding='utf-8', errors='replace') as f:
    html = f.read()
# Find any URLs that look like camera feeds
patterns = [
    r'(?:src|href)="([^"]+\.m3u8)"',
    r'(?:src|href)="([^"]+\.mp4)"',
    r'(?:src|href)="([^"]+\.jpg)"',
    r'(?:src|href)="([^"]+ipcam[^"]*)"',
    r'(?:src|href)="(https?://[^"]+/cam[^"]*)"',
    r'(?:src|href)="(https?://[^"]+\.mjpg)"',
]
for pat in patterns:
    matches = re.findall(pat, html, re.I)
    if matches:
        print(f'\n{pat}:')
        for m in matches[:5]:
            print(' ', m[:200])
# Find embedded video
videos = re.findall(r'<video[^>]+src="([^"]+)"', html, re.I)
if videos:
    print('\nVideo tags:')
    for v in videos:
        print(' ', v[:200])
# Find iframe
iframes = re.findall(r'<iframe[^>]+src="([^"]+)"', html, re.I)
if iframes:
    print('\nIframes:')
    for v in iframes:
        print(' ', v[:200])
