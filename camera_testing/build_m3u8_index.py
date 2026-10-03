"""Build a static HTML index of every .m3u8 entry in the CSV.
Single HTML file that opens in any browser — clickable thumbnail grid."""
import csv
import json
import os
import re
import urllib.parse

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
OUT_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\m3u8_index.html'

PLAYER_PATH = 'hls_player.html'  # sibling file


def main():
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    m3u8_rows = []
    for r in rows[1:]:
        if len(r) > 3 and r[3] and '.m3u8' in r[3].lower():
            m3u8_rows.append({
                'idx': r[0],
                'name': r[1] if len(r) > 1 else '',
                'country': r[19] if len(r) > 19 else '',
                'region': r[20] if len(r) > 20 else '',
                'city': r[21] if len(r) > 21 else '',
                'lat': r[23] if len(r) > 23 else '',
                'lon': r[24] if len(r) > 24 else '',
                'url': r[3],
                'host': r[29] if len(r) > 29 else '',
                'source': (r[31].split('source=')[1].split(',')[0].split(';')[0]
                           if len(r) > 31 and 'source=' in r[31] else ''),
            })
    print(f'total m3u8 entries: {len(m3u8_rows)}')

    # Thumbnail: use Windy imgproxy-style fallback to first-frame for any cam.
    # Most .m3u8 won't have a thumbnail. We use a generic cam icon.
    thumb = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180">'
        '<rect width="320" height="180" fill="#222"/>'
        '<circle cx="160" cy="80" r="35" fill="#444"/>'
        '<rect x="120" y="100" width="80" height="50" rx="6" fill="#666"/>'
        '<text x="160" y="170" fill="#aaa" font-size="12" text-anchor="middle" font-family="monospace">CAM</text>'
        '</svg>'
    )

    # Generate HTML
    out = ['<!doctype html><html><head><meta charset="utf-8"><title>m3u8 Index</title>',
           '<style>',
           'body{margin:0;background:#111;color:#eee;font-family:system-ui;padding:8px}',
           '#search{width:100%;padding:8px;background:#000;color:#0f0;border:1px solid #444;font-size:14px;margin-bottom:8px}',
           '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px}',
           '.card{background:#222;border:1px solid #333;padding:8px;border-radius:4px;text-decoration:none;color:inherit;display:block}',
           '.card:hover{background:#2a2a2a;border-color:#0c0}',
           '.name{font-weight:bold;font-size:13px;line-height:1.2;height:32px;overflow:hidden}',
           '.meta{color:#888;font-size:11px;margin-top:4px;font-family:monospace}',
           '.url{color:#0c0;font-size:10px;word-break:break-all;font-family:monospace;margin-top:4px}',
           'img{display:block;width:100%;height:auto;background:#000}',
           '.h{font-size:11px;color:#888;margin:8px 0}',
           '</style></head><body>',
           f'<input id="search" placeholder="filter by name, country, host, idx ({len(m3u8_rows)} entries)...">',
           '<div class="h">click any card to open in player</div>',
           '<div class="grid" id="grid">']

    for r in m3u8_rows[:2000]:  # cap for browser speed
        url_q = urllib.parse.quote(r['url'], safe='')
        href = f'{PLAYER_PATH}?url={url_q}'
        meta = ', '.join(filter(None, [r['city'], r['region'], r['country']]))
        out.append(
            f'<a class="card" href="{href}" data-name="{r["name"]}" data-country="{r["country"]}" data-host="{r["host"]}" data-idx="{r["idx"]}">'
            f'<img src="data:image/svg+xml;utf8,{urllib.parse.quote(thumb)}" alt="cam">'
            f'<div class="name">{r["name"]}</div>'
            f'<div class="meta">#{r["idx"]} | {r["source"]} | {meta}</div>'
            f'<div class="url">{r["host"]}</div>'
            f'</a>'
        )
    out.append('</div><script>')
    out.append('const cards = document.querySelectorAll(".card");')
    out.append('document.getElementById("search").addEventListener("input", e => {')
    out.append('  const q = e.target.value.toLowerCase();')
    out.append('  cards.forEach(c => {')
    out.append('    const text = (c.dataset.name + " " + c.dataset.country + " " + c.dataset.host + " " + c.dataset.idx).toLowerCase();')
    out.append('    c.style.display = text.includes(q) ? "" : "none";')
    out.append('  });')
    out.append('});')
    out.append('</script></body></html>')

    html = '\n'.join(out)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'wrote {OUT_PATH} ({len(html) // 1024} KB)')


if __name__ == '__main__':
    main()
