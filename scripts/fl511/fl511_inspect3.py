"""Find JS scripts in fl511 page."""
import re

with open('fl511_cctv_page.html', 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()
print(f'HTML size: {len(html):,}')
for m in re.finditer(r'src="([^"]+\.js[^"]*)"', html):
    print(m.group(1))
